#!/bin/bash
# Pi Node Setup Script for LLM Transcript Generator
# Run with: bash setup_pi_node.sh

set -e  # Exit on any error

echo "🚀 Setting up Pi Node for LLM Transcript Generator..."
echo "=================================================="

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Python and pip
echo "🐍 Installing Python and pip..."
sudo apt install -y python3 python3-pip python3-venv git curl wget

# Install audio development libraries (required for PyAudio)
echo "🎧 Installing audio development libraries..."
sudo apt install -y portaudio19-dev python3-dev libasound2-dev

# Verify Python version
python3 --version
pip3 --version

# Verify we're in the correct directory
echo "📁 Verifying repository structure..."
if [ ! -f "requirements.txt" ] || [ ! -d "src" ]; then
    echo "❌ Error: Not in repository root directory"
    echo "Please run this script from the lex-transcript-generator directory"
    exit 1
fi
echo "✅ Repository structure verified"

# Create virtual environment
echo "🔧 Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📋 Installing Python dependencies..."
pip install -r requirements.txt

# Detect if running on Pi
if grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null || [ "$(uname -m)" = "aarch64" ] || [ "$(uname -m)" = "armv7l" ]; then
    echo "🍓 Raspberry Pi detected - installing llama.cpp..."
    
    # Install build dependencies
    sudo apt install -y build-essential cmake git libcurl4-openssl-dev
    
    # Clone and build llama.cpp
    cd ~
    if [ ! -d "llama.cpp" ]; then
        git clone https://github.com/ggerganov/llama.cpp.git
        cd llama.cpp
        mkdir build
        cd build
        cmake .. -DLLAMA_CURL=OFF
        cmake --build . --config Release -j$(nproc)
    else
        echo "llama.cpp already exists, updating..."
        cd llama.cpp
        git pull
        mkdir -p build
        cd build
        cmake .. -DLLAMA_CURL=OFF
        cmake --build . --config Release -j$(nproc)
    fi
    
    # Setup models directory
    echo "📥 Setting up models..."
    mkdir -p models
    cd models
    
    # Check for local models first
    SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"  # Get script directory
    LOCAL_MODELS_DIR="$SCRIPT_DIR/models"
    
    # Copy Gemma model from local if available
    if [ -f "$LOCAL_MODELS_DIR/gemma-1.1-2b-it-Q4_K_M.gguf" ]; then
        echo "📁 Found local Gemma model, copying..."
        cp "$LOCAL_MODELS_DIR/gemma-1.1-2b-it-Q4_K_M.gguf" .
    elif [ ! -f "gemma-1.1-2b-it-Q4_K_M.gguf" ]; then
        echo "🌐 Downloading Gemma 1B model..."
        wget "https://huggingface.co/bartowski/gemma-1.1-2b-it-GGUF/resolve/main/gemma-1.1-2b-it-Q4_K_M.gguf"
    fi
    
    # Copy embedding model from local if available
    if [ -f "$LOCAL_MODELS_DIR/nomic-embed-text-v1.5.f16.gguf" ]; then
        echo "📁 Found local embedding model, copying..."
        cp "$LOCAL_MODELS_DIR/nomic-embed-text-v1.5.f16.gguf" .
    elif [ ! -f "nomic-embed-text-v1.5.f16.gguf" ]; then
        echo "🌐 Downloading embedding model..."
        wget "https://huggingface.co/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.f16.gguf"
    fi
    
    # Create startup script for llama.cpp server
    cd ~/llama.cpp
    cat > start_server.sh << 'EOF'
#!/bin/bash
echo "Starting llama.cpp server on port 1234..."
./build/bin/llama-server -m models/gemma-1.1-2b-it-Q4_K_M.gguf --port 1234 --host 0.0.0.0 -c 2048 -ngl 0
EOF
    chmod +x start_server.sh
    
    echo "✅ llama.cpp installed with Gemma 1B model"
    LLAMA_CPP_INSTALLED=true
else
    echo "🖥️ Desktop detected - installing LM Studio..."
    cd ~
    if [ ! -f "LM_Studio-0.2.31.AppImage" ]; then
        echo "Downloading LM Studio AppImage..."
        wget -O LM_Studio-0.2.31.AppImage "https://releases.lmstudio.ai/linux/x86/0.2.31/LM_Studio-0.2.31.AppImage"
        chmod +x LM_Studio-0.2.31.AppImage
        
        # Create desktop shortcut
        mkdir -p ~/.local/share/applications
        cat > ~/.local/share/applications/lmstudio.desktop << EOF
[Desktop Entry]
Name=LM Studio
Exec=$HOME/LM_Studio-0.2.31.AppImage
Icon=application-x-executable
Type=Application
Categories=Development;
EOF
        
        echo "✅ LM Studio installed! Launch with: ~/LM_Studio-0.2.31.AppImage"
    else
        echo "✅ LM Studio already installed"
    fi
    LLAMA_CPP_INSTALLED=false
fi

# Return to project directory and find it
if [ -n "$OLDPWD" ] && [ -f "$OLDPWD/requirements.txt" ]; then
    PROJECT_DIR="$OLDPWD"
else
    # Try to find project directory
    PROJECT_DIR=$(find /home -name "LLM-Transcript-Data-Gen" -type d 2>/dev/null | head -1)
    if [ -z "$PROJECT_DIR" ]; then
        PROJECT_DIR=$(find /home -name "lex-transcript-generator" -type d 2>/dev/null | head -1)
    fi
fi

if [ -z "$PROJECT_DIR" ] || [ ! -f "$PROJECT_DIR/requirements.txt" ]; then
    echo "❌ Cannot find project directory"
    echo "Please run this script from the project root directory"
    exit 1
fi

cd "$PROJECT_DIR"
echo "📁 Using project directory: $PROJECT_DIR"

# Activate virtual environment for health check
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found at $PROJECT_DIR/.venv"
    echo "Please run this script from the project root directory"
    exit 1
fi

echo ""
echo "🏥 Running health check..."
echo "========================="

# Run health check
if python scripts/health_check.py; then
    echo ""
    echo "🎉 SUCCESS! Pi node setup complete!"
    echo "=================================="
    echo ""
    echo "📋 NEXT STEPS:"
    if [ "$LLAMA_CPP_INSTALLED" = "true" ]; then
        echo "🍓 Raspberry Pi Setup:"
        echo "1. Start llama.cpp server:"
        echo "   cd ~/llama.cpp"
        echo "   ./start_server.sh"
        echo ""
        echo "2. In another terminal, test the setup:"
        echo "   cd ~/lex-transcript-generator"
        echo "   source .venv/bin/activate"
        echo "   python src/nodes/generation_node.py 1"
        echo ""
        echo "3. Start production node:"
        echo "   python src/nodes/generation_node.py"
        echo ""
        echo "🔗 Verify server: http://localhost:1234/v1/models"
        echo "📝 Note: Pi uses Gemma 1B model (optimized for ARM)"
        echo "💾 Models location: ~/llama.cpp/models/"
    else
        echo "🖥️ Desktop Setup:"
        echo "1. Start LM Studio: ~/LM_Studio-0.2.31.AppImage"
        echo "2. In LM Studio:"
        echo "   - Download 'gamma-1b' model (chat)"
        echo "   - Download 'nomic-embed' model (embedding)"
        echo "   - Load the gamma-1b model"
        echo "   - Go to 'Local Server' tab and click 'Start Server'"
        echo ""
        echo "3. Test the setup:"
        echo "   cd ~/lex-transcript-generator"
        echo "   source .venv/bin/activate"
        echo "   python src/nodes/generation_node.py 1"
        echo ""
        echo "4. Start production node:"
        echo "   python src/nodes/generation_node.py"
        echo ""
        echo "🔗 Verify LM Studio server: http://localhost:1234/v1/models"
    fi
    echo ""
else
    echo ""
    echo "❌ Health check failed. Please check the errors above."
    echo "💡 You may need to configure the database connection manually."
    echo ""
    echo "📋 Manual setup steps:"
    if [ "$LLAMA_CPP_INSTALLED" = "true" ]; then
        echo "1. Start llama.cpp server: cd ~/llama.cpp && ./start_server.sh"
    else
        echo "1. Start LM Studio and load models"
    fi
    echo "2. Run: python scripts/health_check.py"
    echo "3. Follow the interactive prompts"
fi

echo ""
echo "📁 Project location: $(pwd)"
echo "🔧 Activate environment: source .venv/bin/activate"
echo ""
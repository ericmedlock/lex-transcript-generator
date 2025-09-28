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

# Verify Python version
python3 --version
pip3 --version

# Clone repository
echo "📥 Cloning repository..."
if [ -d "lex-transcript-generator" ]; then
    echo "Repository already exists, pulling latest..."
    cd lex-transcript-generator
    git pull
else
    git clone https://github.com/ericmedlock/lex-transcript-generator.git
    cd lex-transcript-generator
fi

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

# Install LM Studio (AppImage for Linux)
echo "🤖 Installing LM Studio..."
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

# Return to project directory
cd ~/lex-transcript-generator

# Activate virtual environment for health check
source .venv/bin/activate

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
    echo ""
else
    echo ""
    echo "❌ Health check failed. Please check the errors above."
    echo "💡 You may need to configure the database connection manually."
    echo ""
    echo "📋 Manual setup steps:"
    echo "1. Start LM Studio and load models"
    echo "2. Run: python scripts/health_check.py"
    echo "3. Follow the interactive prompts"
fi

echo ""
echo "📁 Project location: ~/lex-transcript-generator"
echo "🔧 Activate environment: source .venv/bin/activate"
echo ""
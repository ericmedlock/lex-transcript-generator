#!/usr/bin/env python3
"""
Pi Startup Manager - Auto-setup for Raspberry Pi nodes
"""
import os
import urllib.request
from pathlib import Path

class PiStartupManager:
    def __init__(self):
        # Check llama.cpp models directory first
        self.models_dirs = [
            Path("/home/ericm/llama.cpp/models"),
            Path("/home/ericm/models")
        ]
        # Look for the actual model files from setup script
        self.expected_models = [
            "gemma-1.1-2b-it-Q4_K_M.gguf",
            "nomic-embed-text-v1.5.f16.gguf"
        ]
        self.model_path = None
        self.embedding_path = None
    
    def setup(self):
        """Setup Pi environment"""
        print("[PI] Setting up Raspberry Pi environment...")
        
        # Find models in available directories
        for models_dir in self.models_dirs:
            if not models_dir.exists():
                continue
                
            for model_name in self.expected_models:
                model_path = models_dir / model_name
                if model_path.exists():
                    if "embed" not in model_name.lower():
                        self.model_path = model_path
                        print(f"[PI] Found chat model: {model_name} in {models_dir}")
                    else:
                        self.embedding_path = model_path
                        print(f"[PI] Found embedding model: {model_name} in {models_dir}")
        
        if not self.model_path:
            print(f"[PI] No chat models found in {self.models_dirs}")
            print(f"[PI] Looking for: {self.expected_models}")
            return False
        
        print("[PI] Chat model ready")
        
        # Set CPU governor to performance
        try:
            os.system("echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1")
            print("[PI] CPU governor set to performance")
        except:
            pass
        
        return True
    
    def get_model_path(self):
        """Get path to model file"""
        return str(self.model_path) if self.model_path else None
    
    def teardown(self):
        """Cleanup Pi resources"""
        print("[PI] Cleaning up Pi resources...")
        
        # Reset CPU governor
        try:
            os.system("echo ondemand | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1")
            print("[PI] CPU governor reset to ondemand")
        except:
            pass
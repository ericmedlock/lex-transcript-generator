#!/usr/bin/env python3
"""
Pi Startup Manager - Auto-setup for Raspberry Pi nodes
"""
import os
import urllib.request
from pathlib import Path

class PiStartupManager:
    def __init__(self):
        self.models_dir = Path("/home/ericm/models")
        self.model_path = self.models_dir / "phi-3-mini-4k-instruct.Q4_K_M.gguf"
        self.model_url = "https://huggingface.co/microsoft/Phi-3-mini-4K-instruct-gguf/resolve/main/Phi-3-mini-4K-instruct-q4.gguf"
    
    def setup(self):
        """Setup Pi environment"""
        print("[PI] Setting up Raspberry Pi environment...")
        
        # Create models directory
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Download model if not exists
        if not self.model_path.exists():
            print(f"[PI] Downloading model to {self.model_path}...")
            try:
                urllib.request.urlretrieve(self.model_url, self.model_path)
                print("[PI] Model downloaded successfully")
            except Exception as e:
                print(f"[PI] Model download failed: {e}")
                return False
        else:
            print("[PI] Model already exists")
        
        # Set CPU governor to performance
        try:
            os.system("echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1")
            print("[PI] CPU governor set to performance")
        except:
            pass
        
        return True
    
    def get_model_path(self):
        """Get path to model file"""
        return str(self.model_path)
    
    def teardown(self):
        """Cleanup Pi resources"""
        print("[PI] Cleaning up Pi resources...")
        
        # Reset CPU governor
        try:
            os.system("echo ondemand | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor > /dev/null 2>&1")
            print("[PI] CPU governor reset to ondemand")
        except:
            pass
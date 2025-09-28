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
        # Look for the actual model files you have
        self.expected_models = [
            "gemma-2-2b-it-q4_k_m.gguf",
            "nomic-embed-text-v1.5-q8_0.gguf"
        ]
        self.model_path = self.models_dir / "gemma-2-2b-it-q4_k_m.gguf"
        self.embedding_path = self.models_dir / "nomic-embed-text-v1.5-q8_0.gguf"
    
    def setup(self):
        """Setup Pi environment"""
        print("[PI] Setting up Raspberry Pi environment...")
        
        # Create models directory
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Check for expected models
        missing_models = []
        for model_name in self.expected_models:
            model_path = self.models_dir / model_name
            if not model_path.exists():
                missing_models.append(model_name)
            else:
                print(f"[PI] Found model: {model_name}")
        
        if missing_models:
            print(f"[PI] No chat models found in {self.models_dir}")
            print(f"[PI] Looking for: {self.expected_models}")
            print("[PI] Environment setup failed")
            return False
        
        print("[PI] All required models found")
        
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
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
        # Use existing models instead of downloading
        self.available_models = [
            "gemma-2-2b-it-q4_k_m.gguf",
            "nomic-embed-text-v1.5-q8_0.gguf"
        ]
        self.model_path = None
    
    def setup(self):
        """Setup Pi environment"""
        print("[PI] Setting up Raspberry Pi environment...")
        
        # Check for existing models
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # Find available chat model (not embedding)
        for model_name in self.available_models:
            model_path = self.models_dir / model_name
            if model_path.exists() and "embed" not in model_name.lower():
                self.model_path = model_path
                print(f"[PI] Found model: {model_name}")
                break
        
        if not self.model_path:
            print(f"[PI] No chat models found in {self.models_dir}")
            print(f"[PI] Looking for: {self.available_models}")
            return False
        
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
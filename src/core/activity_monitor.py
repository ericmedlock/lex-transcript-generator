#!/usr/bin/env python3
"""
Activity Monitor - Detect user activity and system load
"""

import psutil
import time
import platform
import subprocess
from datetime import datetime

class ActivityMonitor:
    def __init__(self, config):
        self.config = config.get("resource_management", {})
        self.activity_detection = self.config.get("activity_detection", True)
        self.check_interval = self.config.get("check_interval", 5)
        self.temp_limit = self.config.get("temp_limit", 80)
        
        self.gaming_processes = [
            "steam.exe", "steamwebhelper.exe", "epicgameslauncher.exe",
            "battle.net.exe", "riotclientservices.exe", "minecraft.exe",
            "chrome.exe", "firefox.exe", "msedge.exe"
        ]
        
        self.last_activity_check = 0
        self.current_mode = "idle"
    
    def get_cpu_usage(self):
        """Get current CPU usage percentage"""
        return psutil.cpu_percent(interval=1)
    
    def get_gpu_usage(self):
        """Get GPU usage if available"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["nvidia-smi", "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return float(result.stdout.strip())
        except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
            pass
        return 0
    
    def get_cpu_temp(self):
        """Get CPU temperature if available"""
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if entry.current:
                            return entry.current
        except (AttributeError, OSError):
            pass
        return 0
    
    def detect_gaming_activity(self):
        """Detect if gaming or intensive apps are running"""
        try:
            for proc in psutil.process_iter(['name', 'cpu_percent']):
                proc_name = proc.info['name'].lower()
                if any(game in proc_name for game in self.gaming_processes):
                    cpu_usage = proc.info.get('cpu_percent', 0)
                    if cpu_usage > 5:  # Active process
                        return True, proc_name
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        return False, None
    
    def get_activity_mode(self):
        """Determine current activity mode based on CPU/GPU usage only"""
        if not self.activity_detection:
            return "idle"
        
        # Check every few seconds to avoid overhead
        now = time.time()
        if now - self.last_activity_check < self.check_interval:
            return self.current_mode
        
        self.last_activity_check = now
        
        # Check CPU and GPU usage (ignore specific applications)
        cpu_usage = self.get_cpu_usage()
        gpu_usage = self.get_gpu_usage()
        cpu_temp = self.get_cpu_temp()
        
        # Determine mode based on resource usage thresholds
        if cpu_temp > self.temp_limit:
            self.current_mode = "thermal_throttle"
        elif cpu_usage > 80 or gpu_usage > 70:
            self.current_mode = "heavy_load"
        elif cpu_usage > 50 or gpu_usage > 40:
            self.current_mode = "active"
        elif cpu_usage > 20 or gpu_usage > 15:
            self.current_mode = "light_load"
        else:
            self.current_mode = "idle"
        
        return self.current_mode
    
    def get_resource_limits(self):
        """Get current resource limits with gradual ramp up/down"""
        mode = self.get_activity_mode()
        
        # Gradual throttling based on current load
        if mode == "thermal_throttle":
            return {"cpu_limit": 5, "gpu_limit": 5, "delay": 30, "throttle_factor": 0.1}
        elif mode == "heavy_load":
            return {"cpu_limit": 15, "gpu_limit": 10, "delay": 15, "throttle_factor": 0.2}
        elif mode == "active":
            return {"cpu_limit": 30, "gpu_limit": 25, "delay": 8, "throttle_factor": 0.4}
        elif mode == "light_load":
            return {"cpu_limit": 50, "gpu_limit": 40, "delay": 3, "throttle_factor": 0.7}
        else:  # idle
            return {"cpu_limit": 85, "gpu_limit": 80, "delay": 1, "throttle_factor": 1.0}
    
    def should_throttle(self):
        """Check if processing should be throttled with gradual scaling"""
        limits = self.get_resource_limits()
        current_cpu = self.get_cpu_usage()
        current_gpu = self.get_gpu_usage()
        
        # Return throttle status and scaling factor
        cpu_over = current_cpu > limits["cpu_limit"]
        gpu_over = current_gpu > limits["gpu_limit"]
        
        return cpu_over or gpu_over
    
    def get_throttle_factor(self):
        """Get current throttle factor (0.1 = 10% capacity, 1.0 = full capacity)"""
        limits = self.get_resource_limits()
        return limits.get("throttle_factor", 1.0)
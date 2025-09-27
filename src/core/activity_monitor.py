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
        """Determine current activity mode"""
        if not self.activity_detection:
            return "idle"
        
        # Check every few seconds to avoid overhead
        now = time.time()
        if now - self.last_activity_check < self.check_interval:
            return self.current_mode
        
        self.last_activity_check = now
        
        # Check CPU usage
        cpu_usage = self.get_cpu_usage()
        gpu_usage = self.get_gpu_usage()
        
        # Check for gaming/intensive apps
        gaming_active, proc_name = self.detect_gaming_activity()
        
        # Check temperature
        cpu_temp = self.get_cpu_temp()
        
        # Determine mode
        if cpu_temp > self.temp_limit:
            self.current_mode = "thermal_throttle"
        elif gaming_active:
            self.current_mode = "gaming"
        elif cpu_usage > 70 or gpu_usage > 50:
            self.current_mode = "active"
        else:
            self.current_mode = "idle"
        
        return self.current_mode
    
    def get_resource_limits(self):
        """Get current resource limits based on activity"""
        mode = self.get_activity_mode()
        
        if mode == "thermal_throttle":
            return {"cpu_limit": 10, "gpu_limit": 5, "delay": 30}
        elif mode == "gaming":
            return {
                "cpu_limit": self.config.get("cpu_limit_active", 20),
                "gpu_limit": self.config.get("gpu_limit_active", 10),
                "delay": 10
            }
        elif mode == "active":
            return {
                "cpu_limit": self.config.get("cpu_limit_active", 30),
                "gpu_limit": self.config.get("gpu_limit_active", 20),
                "delay": 5
            }
        else:  # idle
            return {
                "cpu_limit": self.config.get("cpu_limit_idle", 80),
                "gpu_limit": self.config.get("gpu_limit_idle", 70),
                "delay": 1
            }
    
    def should_throttle(self):
        """Check if processing should be throttled"""
        limits = self.get_resource_limits()
        current_cpu = self.get_cpu_usage()
        current_gpu = self.get_gpu_usage()
        
        return (current_cpu > limits["cpu_limit"] or 
                current_gpu > limits["gpu_limit"])
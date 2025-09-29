import psutil
import threading
import time
from typing import Dict, List
import GPUtil

class ResourceMonitor:
    def __init__(self):
        self.monitoring = False
        self.metrics = []
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Start resource monitoring in background thread"""
        self.monitoring = True
        self.metrics = []
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
    
    def stop_monitoring(self) -> Dict:
        """Stop monitoring and return aggregated metrics"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        if not self.metrics:
            return {
                "cpu_usage_avg": 0,
                "cpu_usage_max": 0,
                "cpu_temp_avg": 0,
                "cpu_temp_max": 0,
                "gpu_usage_avg": 0,
                "gpu_usage_max": 0,
                "gpu_temp_avg": 0,
                "gpu_temp_max": 0,
                "memory_usage_avg": 0,
                "memory_usage_max": 0
            }
        
        # Calculate averages and maximums
        cpu_usages = [m["cpu_usage"] for m in self.metrics]
        cpu_temps = [m["cpu_temp"] for m in self.metrics if m["cpu_temp"] is not None]
        gpu_usages = [m["gpu_usage"] for m in self.metrics if m["gpu_usage"] is not None]
        gpu_temps = [m["gpu_temp"] for m in self.metrics if m["gpu_temp"] is not None]
        memory_usages = [m["memory_usage"] for m in self.metrics]
        
        return {
            "cpu_usage_avg": sum(cpu_usages) / len(cpu_usages) if cpu_usages else 0,
            "cpu_usage_max": max(cpu_usages) if cpu_usages else 0,
            "cpu_temp_avg": sum(cpu_temps) / len(cpu_temps) if cpu_temps else 0,
            "cpu_temp_max": max(cpu_temps) if cpu_temps else 0,
            "gpu_usage_avg": sum(gpu_usages) / len(gpu_usages) if gpu_usages else 0,
            "gpu_usage_max": max(gpu_usages) if gpu_usages else 0,
            "gpu_temp_avg": sum(gpu_temps) / len(gpu_temps) if gpu_temps else 0,
            "gpu_temp_max": max(gpu_temps) if gpu_temps else 0,
            "memory_usage_avg": sum(memory_usages) / len(memory_usages) if memory_usages else 0,
            "memory_usage_max": max(memory_usages) if memory_usages else 0
        }
    
    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                # CPU metrics
                cpu_usage = psutil.cpu_percent(interval=None)
                memory_usage = psutil.virtual_memory().percent
                
                # CPU temperature (if available)
                cpu_temp = None
                try:
                    temps = psutil.sensors_temperatures()
                    if temps:
                        # Try common temperature sensor names
                        for sensor_name in ['coretemp', 'cpu_thermal', 'acpi']:
                            if sensor_name in temps:
                                cpu_temp = temps[sensor_name][0].current
                                break
                except:
                    pass
                
                # GPU metrics (if available)
                gpu_usage = None
                gpu_temp = None
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu = gpus[0]  # Use first GPU
                        gpu_usage = gpu.load * 100
                        gpu_temp = gpu.temperature
                except:
                    pass
                
                self.metrics.append({
                    "timestamp": time.time(),
                    "cpu_usage": cpu_usage,
                    "cpu_temp": cpu_temp,
                    "gpu_usage": gpu_usage,
                    "gpu_temp": gpu_temp,
                    "memory_usage": memory_usage
                })
                
                time.sleep(1)  # Sample every second
                
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(1)
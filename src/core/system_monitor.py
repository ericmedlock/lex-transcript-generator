#!/usr/bin/env python3
"""
System Monitor - Collect hardware metrics for nodes
"""

import psutil
import json
from datetime import datetime

class SystemMonitor:
    def __init__(self):
        pass
    
    def get_system_metrics(self):
        """Get current system metrics"""
        try:
            metrics = {
                "timestamp": datetime.now().isoformat(),
                "cpu_percent": round(psutil.cpu_percent(interval=0.1), 1),
                "memory_percent": round(psutil.virtual_memory().percent, 1),
                "memory_used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
                "disk_percent": round(psutil.disk_usage('/').percent, 1) if hasattr(psutil.disk_usage('/'), 'percent') else None,
                "cpu_temp": self.get_cpu_temperature(),
                "gpu_usage": None,
                "gpu_temp": None,
                "gpu_memory_used": None,
                "gpu_memory_total": None
            }
            
            # Try to get GPU metrics
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)  # First GPU
                
                # Get GPU utilization
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                
                # Get GPU temperature
                temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                
                # Get GPU memory
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                
                metrics.update({
                    "gpu_usage": round(util.gpu, 1),
                    "gpu_temp": round(temp, 1),
                    "gpu_memory_used": round(mem_info.used / (1024**3), 1),  # GB
                    "gpu_memory_total": round(mem_info.total / (1024**3), 1)  # GB
                })
                
                pynvml.nvmlShutdown()
            except ImportError:
                pass  # pynvml not available
            except Exception:
                pass  # GPU not available or other error
            
            return metrics
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "cpu_percent": None,
                "memory_percent": None,
                "gpu_usage": None
            }
    
    def get_cpu_temperature(self):
        """Get CPU temperature if available"""
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                # Try common temperature sensor names
                for sensor_name in ['coretemp', 'cpu_thermal', 'acpi']:
                    if sensor_name in temps:
                        return round(temps[sensor_name][0].current, 1)
                
                # Fallback to first available sensor
                first_sensor = list(temps.values())[0]
                if first_sensor:
                    return round(first_sensor[0].current, 1)
        except:
            pass
        
        return None
    
    def get_metrics_json(self):
        """Get metrics as JSON string"""
        return json.dumps(self.get_system_metrics())
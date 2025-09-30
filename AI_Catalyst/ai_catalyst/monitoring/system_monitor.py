"""
System Monitor - Hardware detection and performance monitoring

Provides system metrics collection, hardware detection, and performance monitoring.
"""

import json
import platform
import socket
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class SystemMonitor:
    """System monitoring and hardware detection"""
    
    def __init__(self):
        self._psutil_available = self._check_psutil()
        self._gpu_available = self._check_gpu_support()
    
    def _check_psutil(self) -> bool:
        """Check if psutil is available"""
        try:
            import psutil
            return True
        except ImportError:
            logger.warning("psutil not available, system monitoring limited")
            return False
    
    def _check_gpu_support(self) -> bool:
        """Check if GPU monitoring is available"""
        try:
            import pynvml
            pynvml.nvmlInit()
            pynvml.nvmlShutdown()
            return True
        except ImportError:
            logger.info("pynvml not available, GPU monitoring disabled")
            return False
        except Exception:
            logger.info("No NVIDIA GPU detected")
            return False
    
    def get_system_info(self) -> Dict[str, Any]:
        """
        Get static system information
        
        Returns:
            Dict with system information
        """
        info = {
            'hostname': socket.gethostname(),
            'platform': platform.platform(),
            'system': platform.system(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'python_version': platform.python_version(),
            'cpu_count': None,
            'memory_total_gb': None,
            'gpu_count': 0,
            'gpu_names': []
        }
        
        if self._psutil_available:
            import psutil
            info['cpu_count'] = psutil.cpu_count()
            info['memory_total_gb'] = round(psutil.virtual_memory().total / (1024**3), 1)
        
        if self._gpu_available:
            try:
                import pynvml
                pynvml.nvmlInit()
                gpu_count = pynvml.nvmlDeviceGetCount()
                info['gpu_count'] = gpu_count
                
                gpu_names = []
                for i in range(gpu_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    name = pynvml.nvmlDeviceGetName(handle).decode('utf-8')
                    gpu_names.append(name)
                
                info['gpu_names'] = gpu_names
                pynvml.nvmlShutdown()
            except Exception as e:
                logger.warning(f"Failed to get GPU info: {e}")
        
        return info
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get current system performance metrics
        
        Returns:
            Dict with current metrics
        """
        metrics = {
            'timestamp': datetime.now().isoformat(),
            'cpu_percent': None,
            'memory_percent': None,
            'memory_used_gb': None,
            'memory_total_gb': None,
            'disk_percent': None,
            'cpu_temp': None,
            'gpu_metrics': [],
            'network_io': None,
            'disk_io': None
        }
        
        if not self._psutil_available:
            metrics['error'] = 'psutil not available'
            return metrics
        
        try:
            import psutil
            
            # CPU metrics
            metrics['cpu_percent'] = round(psutil.cpu_percent(interval=0.1), 1)
            
            # Memory metrics
            memory = psutil.virtual_memory()
            metrics['memory_percent'] = round(memory.percent, 1)
            metrics['memory_used_gb'] = round(memory.used / (1024**3), 1)
            metrics['memory_total_gb'] = round(memory.total / (1024**3), 1)
            
            # Disk metrics
            try:
                disk = psutil.disk_usage('/')
                metrics['disk_percent'] = round(disk.percent, 1)
            except:
                # Windows fallback
                try:
                    disk = psutil.disk_usage('C:\\')
                    metrics['disk_percent'] = round(disk.percent, 1)
                except:
                    pass
            
            # CPU temperature
            metrics['cpu_temp'] = self._get_cpu_temperature()
            
            # Network I/O
            try:
                net_io = psutil.net_io_counters()
                metrics['network_io'] = {
                    'bytes_sent': net_io.bytes_sent,
                    'bytes_recv': net_io.bytes_recv
                }
            except:
                pass
            
            # Disk I/O
            try:
                disk_io = psutil.disk_io_counters()
                metrics['disk_io'] = {
                    'read_bytes': disk_io.read_bytes,
                    'write_bytes': disk_io.write_bytes
                }
            except:
                pass
            
        except Exception as e:
            metrics['error'] = str(e)
        
        # GPU metrics
        if self._gpu_available:
            metrics['gpu_metrics'] = self._get_gpu_metrics()
        
        return metrics
    
    def _get_cpu_temperature(self) -> Optional[float]:
        """Get CPU temperature if available"""
        if not self._psutil_available:
            return None
        
        try:
            import psutil
            temps = psutil.sensors_temperatures()
            if temps:
                # Try common temperature sensor names
                for sensor_name in ['coretemp', 'cpu_thermal', 'acpi', 'k10temp']:
                    if sensor_name in temps:
                        sensors = temps[sensor_name]
                        if sensors:
                            return round(sensors[0].current, 1)
                
                # Fallback to first available sensor
                first_sensor = list(temps.values())[0]
                if first_sensor:
                    return round(first_sensor[0].current, 1)
        except Exception:
            pass
        
        return None
    
    def _get_gpu_metrics(self) -> List[Dict[str, Any]]:
        """Get GPU metrics for all available GPUs"""
        gpu_metrics = []
        
        if not self._gpu_available:
            return gpu_metrics
        
        try:
            import pynvml
            pynvml.nvmlInit()
            
            gpu_count = pynvml.nvmlDeviceGetCount()
            
            for i in range(gpu_count):
                handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                
                gpu_metric = {
                    'gpu_id': i,
                    'name': pynvml.nvmlDeviceGetName(handle).decode('utf-8'),
                    'usage_percent': None,
                    'memory_used_gb': None,
                    'memory_total_gb': None,
                    'temperature': None,
                    'power_usage': None
                }
                
                try:
                    # GPU utilization
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                    gpu_metric['usage_percent'] = round(util.gpu, 1)
                    
                    # GPU memory
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    gpu_metric['memory_used_gb'] = round(mem_info.used / (1024**3), 1)
                    gpu_metric['memory_total_gb'] = round(mem_info.total / (1024**3), 1)
                    
                    # GPU temperature
                    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
                    gpu_metric['temperature'] = round(temp, 1)
                    
                    # Power usage
                    try:
                        power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0  # Convert to watts
                        gpu_metric['power_usage'] = round(power, 1)
                    except:
                        pass
                    
                except Exception as e:
                    gpu_metric['error'] = str(e)
                
                gpu_metrics.append(gpu_metric)
            
            pynvml.nvmlShutdown()
            
        except Exception as e:
            logger.error(f"Failed to get GPU metrics: {e}")
        
        return gpu_metrics
    
    def get_thermal_status(self) -> Dict[str, Any]:
        """
        Get thermal status and warnings
        
        Returns:
            Dict with thermal status
        """
        status = {
            'cpu_temp': None,
            'cpu_warning': False,
            'gpu_temps': [],
            'gpu_warnings': [],
            'overall_status': 'normal'
        }
        
        # CPU thermal status
        cpu_temp = self._get_cpu_temperature()
        if cpu_temp:
            status['cpu_temp'] = cpu_temp
            status['cpu_warning'] = cpu_temp > 80  # Warning threshold
        
        # GPU thermal status
        gpu_metrics = self._get_gpu_metrics()
        for gpu in gpu_metrics:
            if gpu.get('temperature'):
                status['gpu_temps'].append(gpu['temperature'])
                status['gpu_warnings'].append(gpu['temperature'] > 85)  # Warning threshold
        
        # Overall status
        if status['cpu_warning'] or any(status['gpu_warnings']):
            status['overall_status'] = 'warning'
        
        return status
    
    def get_metrics_json(self) -> str:
        """Get metrics as JSON string"""
        return json.dumps(self.get_system_metrics())
    
    def is_monitoring_available(self) -> Dict[str, bool]:
        """Check what monitoring capabilities are available"""
        return {
            'psutil': self._psutil_available,
            'gpu': self._gpu_available,
            'cpu_temp': self._get_cpu_temperature() is not None,
            'network_io': self._psutil_available,
            'disk_io': self._psutil_available
        }
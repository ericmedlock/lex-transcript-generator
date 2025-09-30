"""
Performance Tuner - Dynamic performance optimization and tuning

Provides performance monitoring, dynamic tuning, and optimization strategies.
"""

import time
import statistics
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data point"""
    timestamp: datetime
    value: float
    metric_type: str
    metadata: Dict[str, Any] = None


class PerformanceTuner:
    """Dynamic performance tuning and optimization"""
    
    def __init__(self, window_size: int = 100, tune_interval: int = 30):
        """
        Initialize performance tuner
        
        Args:
            window_size: Number of metrics to keep in sliding window
            tune_interval: Tuning interval in seconds
        """
        self.window_size = window_size
        self.tune_interval = tune_interval
        self.metrics_history: Dict[str, List[PerformanceMetric]] = {}
        self.tuning_parameters: Dict[str, Any] = {}
        self.last_tune_time = datetime.now()
        self.optimization_callbacks: Dict[str, Callable] = {}
    
    def record_metric(self, metric_type: str, value: float, metadata: Dict[str, Any] = None):
        """
        Record a performance metric
        
        Args:
            metric_type: Type of metric (e.g., 'latency', 'throughput', 'error_rate')
            value: Metric value
            metadata: Additional metadata
        """
        metric = PerformanceMetric(
            timestamp=datetime.now(),
            value=value,
            metric_type=metric_type,
            metadata=metadata or {}
        )
        
        if metric_type not in self.metrics_history:
            self.metrics_history[metric_type] = []
        
        # Add metric and maintain sliding window
        self.metrics_history[metric_type].append(metric)
        if len(self.metrics_history[metric_type]) > self.window_size:
            self.metrics_history[metric_type].pop(0)
    
    def get_metric_stats(self, metric_type: str, window_minutes: int = 5) -> Dict[str, float]:
        """
        Get statistics for a metric type
        
        Args:
            metric_type: Type of metric
            window_minutes: Time window in minutes
            
        Returns:
            Dict with statistics (mean, median, p95, p99, min, max)
        """
        if metric_type not in self.metrics_history:
            return {}
        
        # Filter metrics within time window
        cutoff_time = datetime.now() - timedelta(minutes=window_minutes)
        recent_metrics = [
            m for m in self.metrics_history[metric_type]
            if m.timestamp >= cutoff_time
        ]
        
        if not recent_metrics:
            return {}
        
        values = [m.value for m in recent_metrics]
        
        return {
            'count': len(values),
            'mean': statistics.mean(values),
            'median': statistics.median(values),
            'p95': self._percentile(values, 95),
            'p99': self._percentile(values, 99),
            'min': min(values),
            'max': max(values),
            'stdev': statistics.stdev(values) if len(values) > 1 else 0
        }
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile of values"""
        if not values:
            return 0.0
        
        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)
        
        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            return lower + (upper - lower) * (index - int(index))
    
    def register_optimization_callback(self, parameter_name: str, callback: Callable[[Any], Any]):
        """
        Register callback for parameter optimization
        
        Args:
            parameter_name: Name of parameter to optimize
            callback: Function to call when parameter should be adjusted
        """
        self.optimization_callbacks[parameter_name] = callback
    
    def set_tuning_parameter(self, name: str, value: Any, min_value: Any = None, max_value: Any = None):
        """
        Set a tuning parameter with optional bounds
        
        Args:
            name: Parameter name
            value: Current value
            min_value: Minimum allowed value
            max_value: Maximum allowed value
        """
        self.tuning_parameters[name] = {
            'value': value,
            'min_value': min_value,
            'max_value': max_value,
            'last_adjusted': datetime.now()
        }
    
    def get_tuning_parameter(self, name: str) -> Any:
        """
        Get current value of tuning parameter
        
        Args:
            name: Parameter name
            
        Returns:
            Current parameter value
        """
        if name in self.tuning_parameters:
            return self.tuning_parameters[name]['value']
        return None
    
    def should_tune(self) -> bool:
        """
        Check if it's time to run tuning
        
        Returns:
            True if tuning should be performed
        """
        return (datetime.now() - self.last_tune_time).seconds >= self.tune_interval
    
    def auto_tune(self, target_metrics: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
        """
        Perform automatic tuning based on target metrics
        
        Args:
            target_metrics: Dict of metric_type -> {'target': value, 'tolerance': value}
            
        Returns:
            Dict with tuning results
        """
        if not self.should_tune():
            return {'status': 'skipped', 'reason': 'too_soon'}
        
        tuning_results = {
            'timestamp': datetime.now().isoformat(),
            'adjustments': {},
            'metrics_status': {}
        }
        
        # Analyze current metrics against targets
        for metric_type, target_config in target_metrics.items():
            stats = self.get_metric_stats(metric_type)
            if not stats:
                continue
            
            target_value = target_config['target']
            tolerance = target_config.get('tolerance', 0.1)
            current_value = stats['mean']
            
            deviation = abs(current_value - target_value) / target_value
            tuning_results['metrics_status'][metric_type] = {
                'current': current_value,
                'target': target_value,
                'deviation': deviation,
                'within_tolerance': deviation <= tolerance
            }
            
            # Apply tuning logic based on metric type
            if metric_type == 'latency' and current_value > target_value * (1 + tolerance):
                # Latency too high - try to reduce concurrency or increase resources
                self._tune_for_latency_reduction(tuning_results)
            elif metric_type == 'throughput' and current_value < target_value * (1 - tolerance):
                # Throughput too low - try to increase concurrency
                self._tune_for_throughput_increase(tuning_results)
            elif metric_type == 'error_rate' and current_value > target_value:
                # Error rate too high - reduce load
                self._tune_for_error_reduction(tuning_results)
        
        self.last_tune_time = datetime.now()
        return tuning_results
    
    def _tune_for_latency_reduction(self, results: Dict[str, Any]):
        """Tune parameters to reduce latency"""
        # Example: Reduce concurrency if available
        if 'concurrency' in self.tuning_parameters:
            current = self.tuning_parameters['concurrency']['value']
            min_val = self.tuning_parameters['concurrency']['min_value']
            
            if min_val is None or current > min_val:
                new_value = max(current - 1, min_val or 1)
                self._adjust_parameter('concurrency', new_value, results)
    
    def _tune_for_throughput_increase(self, results: Dict[str, Any]):
        """Tune parameters to increase throughput"""
        # Example: Increase concurrency if available
        if 'concurrency' in self.tuning_parameters:
            current = self.tuning_parameters['concurrency']['value']
            max_val = self.tuning_parameters['concurrency']['max_value']
            
            if max_val is None or current < max_val:
                new_value = min(current + 1, max_val or current + 1)
                self._adjust_parameter('concurrency', new_value, results)
    
    def _tune_for_error_reduction(self, results: Dict[str, Any]):
        """Tune parameters to reduce error rate"""
        # Example: Reduce load by decreasing concurrency
        if 'concurrency' in self.tuning_parameters:
            current = self.tuning_parameters['concurrency']['value']
            min_val = self.tuning_parameters['concurrency']['min_value']
            
            if min_val is None or current > min_val:
                new_value = max(current - 1, min_val or 1)
                self._adjust_parameter('concurrency', new_value, results)
    
    def _adjust_parameter(self, name: str, new_value: Any, results: Dict[str, Any]):
        """Adjust a tuning parameter and call its callback"""
        old_value = self.tuning_parameters[name]['value']
        self.tuning_parameters[name]['value'] = new_value
        self.tuning_parameters[name]['last_adjusted'] = datetime.now()
        
        results['adjustments'][name] = {
            'old_value': old_value,
            'new_value': new_value
        }
        
        # Call optimization callback if registered
        if name in self.optimization_callbacks:
            try:
                self.optimization_callbacks[name](new_value)
                logger.info(f"Adjusted {name} from {old_value} to {new_value}")
            except Exception as e:
                logger.error(f"Failed to apply parameter adjustment for {name}: {e}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Get summary of current performance status
        
        Returns:
            Dict with performance summary
        """
        summary = {
            'timestamp': datetime.now().isoformat(),
            'metrics': {},
            'parameters': {},
            'tuning_status': {
                'last_tune': self.last_tune_time.isoformat(),
                'next_tune_in': max(0, self.tune_interval - (datetime.now() - self.last_tune_time).seconds)
            }
        }
        
        # Add metric summaries
        for metric_type in self.metrics_history:
            summary['metrics'][metric_type] = self.get_metric_stats(metric_type)
        
        # Add parameter values
        for name, param in self.tuning_parameters.items():
            summary['parameters'][name] = {
                'value': param['value'],
                'last_adjusted': param['last_adjusted'].isoformat()
            }
        
        return summary
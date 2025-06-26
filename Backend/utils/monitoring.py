import time
import logging
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps
import statistics
from collections import defaultdict

logger = logging.getLogger(__name__)

class PerformanceMetrics:
    def __init__(self):
        self.metrics = defaultdict(list)
        self.start_times = {}
        
    def start_operation(self, operation_name: str):
        """Start timing an operation"""
        self.start_times[operation_name] = time.time()
        
    def end_operation(self, operation_name: str, metadata: Optional[Dict[str, Any]] = None):
        """End timing an operation and record metrics"""
        if operation_name in self.start_times:
            duration = time.time() - self.start_times[operation_name]
            self.metrics[operation_name].append({
                'duration': duration,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            })
            del self.start_times[operation_name]
            
    def get_operation_stats(self, operation_name: str) -> Dict[str, float]:
        """Get statistics for a specific operation"""
        if operation_name not in self.metrics:
            return {}
            
        durations = [m['duration'] for m in self.metrics[operation_name]]
        return {
            'count': len(durations),
            'mean': statistics.mean(durations),
            'median': statistics.median(durations),
            'min': min(durations),
            'max': max(durations),
            'total': sum(durations)
        }
        
    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get statistics for all operations"""
        return {
            op_name: self.get_operation_stats(op_name)
            for op_name in self.metrics.keys()
        }
        
    def log_operation_stats(self, operation_name: str):
        """Log statistics for a specific operation"""
        stats = self.get_operation_stats(operation_name)
        if stats:
            logger.info(f"Performance stats for {operation_name}:")
            for stat_name, value in stats.items():
                logger.info(f"  {stat_name}: {value:.3f}s")
                
    def log_all_stats(self):
        """Log statistics for all operations"""
        logger.info("Performance statistics summary:")
        for op_name, stats in self.get_all_stats().items():
            logger.info(f"\n{op_name}:")
            for stat_name, value in stats.items():
                logger.info(f"  {stat_name}: {value:.3f}s")

# Global metrics instance
metrics = PerformanceMetrics()

def track_performance(operation_name: str):
    """Decorator to track performance of a function"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics.start_operation(operation_name)
            try:
                result = await func(*args, **kwargs)
                metadata = {
                    'success': True,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                }
                metrics.end_operation(operation_name, metadata)
                return result
            except Exception as e:
                metadata = {
                    'success': False,
                    'error': str(e),
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                }
                metrics.end_operation(operation_name, metadata)
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics.start_operation(operation_name)
            try:
                result = func(*args, **kwargs)
                metadata = {
                    'success': True,
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                }
                metrics.end_operation(operation_name, metadata)
                return result
            except Exception as e:
                metadata = {
                    'success': False,
                    'error': str(e),
                    'args_count': len(args),
                    'kwargs_count': len(kwargs)
                }
                metrics.end_operation(operation_name, metadata)
                raise
                
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator 
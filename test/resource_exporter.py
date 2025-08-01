# file: resource_exporter.py
import time
import psutil
import GPUtil
from prometheus_client import start_http_server, Gauge

# Gauges we’ll expose
CPU_GAUGE = Gauge('app_cpu_usage_percent', 'System CPU usage percent')
GPU_GAUGE = Gauge('gpu_usage_percent',         'Per-GPU utilization %', ['gpu_id'])
MEM_GAUGE = Gauge('app_mem_usage_bytes',       'Process RAM usage (bytes)')

def collect():
    # system CPU %
    CPU_GAUGE.set(psutil.cpu_percent(interval=None))
    # this Python process’s own memory
    MEM_GAUGE.set(psutil.Process().memory_info().rss)
    # all visible GPUs
    for gpu in GPUtil.getGPUs():
        GPU_GAUGE.labels(gpu_id=gpu.id).set(gpu.load * 100)

if __name__ == '__main__':
    # start Prometheus metrics endpoint on :8002/metrics
    start_http_server(8002)
    while True:
        collect()
        time.sleep(5)

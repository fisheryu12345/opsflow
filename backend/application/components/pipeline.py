"""
pipeline.py — OpsFlow Pipeline 引擎行为配置
"""
from conf.env import *

ENABLE_PIPELINE_EVENT_SIGNALS = True
PIPELINE_ENABLE_ROLLBACK = True
ROLLBACK_QUEUE = "default"
PIPELINE_ENABLE_AUTO_EXECUTE_WHEN_ROLL_BACKED = False

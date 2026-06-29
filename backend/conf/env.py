"""
env.py — OPSflow 配置分层入口

使用方式（三选一）：
  1. 默认：export DJANGO_ENV=dev   （本地开发）
  2. UAT：  export DJANGO_ENV=uat
  3. 生产： export DJANGO_ENV=prod
"""
import os

# 1) 加载共享配置（所有环境相同的变量和默认值）
from conf.env_base import *

# 2) 根据环境变量加载环境覆写
DJANGO_ENV = os.environ.get('DJANGO_ENV', 'dev')
env_file = os.path.join(os.path.dirname(__file__), f'env_{DJANGO_ENV}.py')

if os.path.exists(env_file):
    exec(compile(open(env_file, encoding='utf-8').read(), env_file, 'exec'))

"""Setup for opsflow-agent — pip installable agent client"""

from setuptools import setup, find_packages

setup(
    name='opsflow-agent',
    version='0.1.0',
    description='OpsFlow remote execution agent — WebSocket client for script/file execution',
    packages=find_packages(),
    install_requires=[
        'websocket-client>=1.6.0',
    ],
    entry_points={
        'console_scripts': [
            'opsflow-agent=agent.main:main',
        ],
    },
    python_requires='>=3.8',
)

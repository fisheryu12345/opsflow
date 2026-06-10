"""
monitor_adapters.py — Monitor SPI 适配器注册表

各类适配器通过类路径注册，运行时反射加载。
"""
from conf.env import *

MONITOR_ADAPTERS = {
    'datasource': {
        'prometheus': 'monitor.adapters.datasource.prometheus.PrometheusDataSource',
        'influxdb': 'monitor.adapters.datasource.influxdb.InfluxdbDataSource',
        'custom': 'monitor.adapters.datasource.custom.CustomDataSource',
    },
    'notify': {
        'integration_hub': 'monitor.adapters.notify.integration_hub.IntegrationHubNotify',
        'wecom': 'monitor.adapters.notify.wecom.WeComNotify',
        'dingtalk': 'monitor.adapters.notify.dingtalk.DingTalkNotify',
        'email': 'monitor.adapters.notify.email.EmailNotify',
        'sms': 'monitor.adapters.notify.sms.SmsNotify',
    },
    'action': {
        'opsflow': 'monitor.adapters.action.opsflow.OpsflowAction',
        'awx': 'monitor.adapters.action.awx.AwxAction',
        'itsm': 'monitor.adapters.action.itsm.ItsmAction',
    },
    'target_resolver': {
        'cmdb': 'monitor.adapters.target.cmdb.CmdbTargetResolver',
        'static': 'monitor.adapters.target.static.StaticTargetResolver',
    },
}

"""阿里云 ECS SDK 客户端工厂 — 复用集成中心凭证

用法:
    from opsflow.plugins.aliyun_ecs._client import get_ecs_client
    client = get_ecs_client(region="cn-hangzhou")
    resp = client.do_action_with_exception(request)
"""

import logging

logger = logging.getLogger(__name__)


def get_ecs_client(region: str = "cn-hangzhou"):
    """获取阿里云 ECS SDK AcsClient

    从集成中心 aliyun_ecs 连接器读取 access_key_id + access_key_secret 两条凭证。

    Raises:
        ImportError: aliyun-python-sdk-core 未安装
        ValueError: 连接器/凭证未配置
    """
    try:
        from aliyunsdkcore.client import AcsClient
    except ImportError:
        raise ImportError("请安装 aliyun-python-sdk-core 和 aliyun-python-sdk-ecs")

    from integration.models.connector import ConnectorDefinition
    from integration.services.credential_service import decrypt_credential

    try:
        aliyun_def = ConnectorDefinition.objects.get(code="aliyun_ecs")
        instance = aliyun_def.instances.filter(is_active=True).first()
        if not instance:
            raise ValueError(
                "未找到启用的阿里云连接器实例，请先在「集成中心」配置 aliyun_ecs 连接器"
            )
    except ConnectorDefinition.DoesNotExist:
        raise ValueError(
            "未找到 aliyun_ecs 连接器定义，请先执行 python manage.py seed_reference"
        )

    creds = {
        c.name: decrypt_credential(c.encrypted_value)
        for c in instance.credentials.all()
    }
    ak = creds.get("access_key_id", "")
    sk = creds.get("access_key_secret", "")
    if not ak or not sk:
        raise ValueError(
            "阿里云连接器未配置完整的 AccessKey "
            "(需要 access_key_id + access_key_secret 两条凭证记录)"
        )

    logger.info("Aliyun ECS client created for region=%s", region)
    return AcsClient(ak, sk, region)

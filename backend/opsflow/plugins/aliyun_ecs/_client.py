"""阿里云 ECS SDK 客户端工厂 — 复用集成中心凭证"""

import logging

logger = logging.getLogger(__name__)


def get_ecs_client(region: str):
    """获取阿里云 ECS SDK AcsClient"""
    if not region:
        raise ValueError("region 不能为空，请在流程节点中选择地域")
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
            raise ValueError("未找到启用的阿里云连接器实例")
    except ConnectorDefinition.DoesNotExist:
        raise ValueError("未找到 aliyun_ecs 连接器定义")
    creds = {c.name: decrypt_credential(c.encrypted_value) for c in instance.credentials.all()}
    ak = creds.get("access_key_id", "")
    sk = creds.get("access_key_secret", "")
    if not ak or not sk:
        raise ValueError("阿里云连接器未配置完整的 AccessKey")
    logger.info("Aliyun ECS client created for region=%s", region)
    return AcsClient(ak, sk, region)


def resolve_cmdb_region(instance_id: str) -> str:
    """从 CMDB 查询阿里云实例的地域"""
    try:
        from cmdb.services.neo4j_client import graph_driver
        with graph_driver.session() as session:
            result = session.run(
                "MATCH (h:Host {cloud_instance_id: $cid}) RETURN h.region AS region",
                cid=instance_id,
            )
            rec = result.single()
            if rec and rec.get('region'):
                return rec['region']
    except Exception:
        pass
    return ''

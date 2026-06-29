"""TowerBasePlugin — 通过 Ansible Tower REST API 执行的插件基类

子类只需定义 code/name/description/get_form_config()，
执行和轮询由基类统一管理。

执行流程:
  1. execute() → TowerService.launch_job() → 返回 job_id
  2. schedule() → TowerService.poll_job() → 自适应轮询直到完成
"""
import logging

from opsflow.plugins.base import BasePlugin

logger = logging.getLogger(__name__)


class TowerBasePlugin(BasePlugin):
    """通过 Ansible Tower 执行的插件基类

    子类只需定义 code/name/description/get_form_config()，
    执行（execute）和轮询（schedule）由基类统一管理。
    """
    code = "_tower_base"  # 基类不下发到注册表
    _need_schedule = True

    def execute(self, **kwargs) -> dict:
        """Step 1: 通过 Tower REST API 启动作业

        将子类的 code 作为 atom_type，用户参数作为 extra_vars，
        调用 TowerService.launch_job() 触发 Ansible Job Template。

        Returns:
            dict: {"success": True, "data": {"tower_job_id": int, ...}}
                  或 {"success": False, "data": {}, "error": str}
        """
        from opsflow.plugins.ansible.tower_backend import get_tower_service

        tower = get_tower_service()

        # Tower 未配置 → 返回 mock 结果（开发/调试模式）
        if not tower.is_configured():
            return self._mock_execute(**kwargs)

        # 组装 extra_vars
        from opsflow.plugins.ansible.tower_backend.polling import TowerPollingMixin
        extra_vars = TowerPollingMixin.build_extra_vars(
            atom_type=self.code,
            params=kwargs,
        )

        try:
            launch_result = tower.launch_job(extra_vars=extra_vars)
            job_id = launch_result["job_id"]

            if not job_id:
                logger.error("[TowerBasePlugin] 触发作业后未获取到 job_id code=%s", self.code)
                return self._mock_execute(**kwargs)

            logger.info("[TowerBasePlugin] 作业已触发 code=%s job_id=%s", self.code, job_id)
            return {
                "success": True,
                "data": {
                    "tower_job_id": job_id,
                    "tower_status": "pending",
                    "tower_job_url": launch_result.get("job_url", ""),
                },
            }
        except Exception as e:
            logger.exception("[TowerBasePlugin] 触发作业失败 code=%s", self.code)
            return {"success": False, "data": {}, "error": str(e)}

    def schedule(self, context: dict, **kwargs) -> bool | None:
        """Step 2: 轮询 Tower 作业状态

        bamboo-engine 在 execute() 返回后定期调用此方法。

        Args:
            context: execute() 返回的 data.outputs，含 tower_job_id

        Returns:
            True  → 作业完成，继续下一节点
            False → 作业失败
            None  → 继续等待轮询
        """
        tower_job_id = context.get("tower_job_id")
        if not tower_job_id:
            logger.warning("[TowerBasePlugin] schedule 缺少 tower_job_id")
            return False

        from opsflow.plugins.ansible.tower_backend import get_tower_service
        tower = get_tower_service()

        try:
            status_info = tower.get_job_status(tower_job_id)
            current_status = status_info["status"]

            if current_status in ("successful",):
                # 提取结果并合并到 context
                result = tower.extract_result(tower_job_id)
                self._promote_schedule_result(context, result)
                logger.info("[TowerBasePlugin] 作业完成 job_id=%s", tower_job_id)
                return True

            elif current_status in ("failed", "error", "canceled"):
                logger.warning("[TowerBasePlugin] 作业失败 job_id=%s status=%s",
                               tower_job_id, current_status)
                return False

            else:  # pending, waiting, running
                return None  # 继续等待

        except Exception as e:
            logger.warning("[TowerBasePlugin] 轮询异常 job_id=%s: %s", tower_job_id, e)
            return None  # 网络异常时继续等待

    def _promote_schedule_result(self, context: dict, result: dict):
        """将 Tower 执行结果提升到 context 中，供后续节点引用"""
        stdout = result.get("stdout", "")
        artifacts = result.get("artifacts", {})
        structured = result.get("structured", {})
        summary = result.get("summary", {})
        elapsed = result.get("elapsed", 0)

        # 直接修改 context dict（bamboo-engine 会读取修改后的值）
        context.update({
            "stdout": stdout,
            "stderr": "",
            "returncode": 0,
            "artifacts": artifacts,
            "structured": structured,
            "summary": summary,
            "elapsed": elapsed,
            "tower_status": "success",
        })
        # 将 artifacts 中的字段提升到顶层
        if isinstance(artifacts, dict):
            for k, v in artifacts.items():
                if k not in ("stdout", "stderr", "returncode"):
                    context[k] = v

    def _mock_execute(self, **kwargs) -> dict:
        """本地模拟执行 — Tower 未配置时降级

        返回模拟结果，方便前端开发和 gateway 条件测试。
        子类可覆盖此方法以提供更真实的 mock 数据。
        """
        return {
            "success": True,
            "data": {
                "stdout": f"[Mock] {self.name} executed with params: {kwargs}",
                "stderr": "",
                "returncode": 0,
                "tower_job_id": 0,
                "tower_status": "mock",
            },
        }

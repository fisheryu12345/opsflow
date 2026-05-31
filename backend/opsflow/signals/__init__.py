"""Pipeline 信号处理器 — 追踪 BambooDjangoRuntime ERI 状态变更

向后兼容: apps.py 中 from opsflow import signals 仍然有效，
on_post_set_state 从 handlers 模块重新导出。

通过 post_set_state 信号（pipeline.eri.signals）监听 BambooDjangoRuntime
的节点状态变更，同步更新 FlowExecution 状态并记录 OpsLog。

信号发送参数: node_id, to_state, version, root_id, parent_id, loop
"""

from opsflow.signals.handlers import on_post_set_state

__all__ = ['on_post_set_state']

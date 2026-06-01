"""pipeline 构建 - 循环引用检测"""

MAX_SUBPROCESS_DEPTH = 5


def _detect_circular_ref(template, visited=None, depth=0):
    """深度优先检测子流程循环引用

    遍历模板中所有 subprocess 节点，递归检测 A→B→A 循环。
    Raises ValueError 如果检测到循环或超过最大深度。
    """
    if depth > MAX_SUBPROCESS_DEPTH:
        raise ValueError(f"子流程嵌套超过最大深度 {MAX_SUBPROCESS_DEPTH}")

    visited = visited or set()
    if template.id in visited:
        raise ValueError(f"循环引用检测: 模板 '{template.name}' (id={template.id}) 已被引用")
    visited.add(template.id)

    pipeline_tree = template.pipeline_tree or {}
    for node in pipeline_tree.get('nodes', []):
        if node.get('node_type') == 'subprocess':
            target_id = node.get('params', {}).get('target_template_id')
            if not target_id:
                continue
            from opsflow.models import FlowTemplate
            try:
                target = FlowTemplate.objects.get(id=target_id)
            except FlowTemplate.DoesNotExist:
                continue
            _detect_circular_ref(target, visited.copy(), depth + 1)

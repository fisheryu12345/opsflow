#!/usr/bin/env python
"""
批量替换 opsflow .vue 文件中的硬编码中文 → $t() 调用
"""
import glob
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

# Define replacement map: Chinese text → translation key (under message.opsflow.*)
REPLACEMENTS = {
    # ExecutionDetail.vue
    '启动失败': "ElMessage.error(e?.msg || t('message.execution.execFailed'))",
    '暂停失败': "ElMessage.error(e?.msg || t('message.execution.pauseFailed'))",
    '恢复失败': "ElMessage.error(e?.msg || t('message.execution.resumeFailed'))",
    '重试失败': "ElMessage.error(e?.msg || t('message.execution.retryFailed'))",
    '跳过失败': "ElMessage.error(e?.msg || t('message.execution.skipFailed'))",
    '重试已提交': "ElMessage.success(t('message.execution.retrySuccess'))",
    '节点已跳过': "ElMessage.success(t('message.execution.skipSuccess'))",
    '取消失败': "ElMessage.error(e?.msg || t('message.execution.cancelFailed'))",

    # ExecutionDetail.vue - status labels
    "'执行中'": "t('message.execution.statusRunning')",
    "'已完成'": "t('message.execution.statusFinished')",
    "'失败'": "t('message.execution.statusFailed')",
    "'跳过'": "t('message.execution.statusSkipped')",
    "'已取消'": "t('message.execution.statusCancelled')",
    "'等待执行'": "t('message.execution.statusWaiting')",
    "'待执行'": "t('message.execution.statusPending')",
    "'执行成功'": "t('message.execution.statusFinished')",
    "'执行失败'": "t('message.execution.statusFailed')",

    # DesignCanvas.vue
    '请先选择一个节点': "t('message.execution.selectNode')",
    '请选择一个模版': "t('message.template.selectTemplate')",
    '执行失败，未获取到执行 ID': "t('message.canvas.noExecId')",
    'Dry Run 执行失败': "t('message.execution.dryRunFailed')",

    # PluginPickerDialog.vue
    "'配置中'": "t('message.plugin.configuring')",
    "'安装中'": "t('message.plugin.installing')",

    # Canvas toolbar
    '放大': "t('message.canvas.zoomIn')",
    '缩小': "t('message.canvas.zoomOut')",
    '重置缩放': "t('message.canvas.resetZoom')",
    '自动布局': "t('message.canvas.autoLayout')",
    '全屏': "t('message.canvas.fullscreen')",
    '保存': "t('message.canvas.save')",
    '发布': "t('message.canvas.publish')",
    '撤销': "t('message.canvas.undo')",
    '重做': "t('message.canvas.redo')",
    '删除': "t('message.canvas.delete')",
    '复制': "t('message.canvas.copy')",
    '粘贴': "t('message.canvas.paste')",
    '全选': "t('message.canvas.selectAll')",

    # PropertyPanel.vue
    'success->成功分支': "t('message.properties.successBranch')",
    'failure->失败分支': "t('message.properties.failureBranch')",
    'custom->自定义分支': "t('message.properties.customBranch')",

    # Common operations
    '操作成功': "t('message.common.operateSuccess')",
    '操作失败': "t('message.common.operateFailed')",
    '确认删除': "t('message.common.confirmDelete')",
    '加载中...': "t('message.common.loading')",
    '暂无数据': "t('message.common.noData')",
}

# Files to process
files = []
for pattern in [
    "src/views/apps/opsflow/**/*.vue",
    "src/views/apps/opsflow-execution/**/*.vue",
    "src/views/apps/opsflow-schedule/**/*.vue",
]:
    files.extend(glob.glob(f"web/{pattern}", recursive=True))

total_replaced = 0
for fp in sorted(files):
    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    original = content

    # Check if file needs $t imported/defined
    needs_t = False

    for cn_text, replacement in REPLACEMENTS.items():
        count = content.count(cn_text)
        if count > 0:
            needs_t = True
            content = content.replace(cn_text, replacement)
            total_replaced += count

    if content != original:
        # Add t() import if needed
        # Check if already has t defined from useI18n
        if needs_t and 'const { t } = useI18n()' not in content and 'import { useI18n }' not in content:
            # Add t to existing useI18n destructure if present
            if 'const { t } = useI18n()' not in content:
                # Find script setup and add after the setup tag
                # Different options depending on structure
                pass  # Manual check needed

        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[OK] {fp}: {len([k for k in REPLACEMENTS if k in original])} patterns matched, file updated")

print(f"\nTotal replacements: {total_replaced}")
print("\nNOTE: Some files may need manual t() imports added.")

#!/usr/bin/env python
"""Batch i18n fix: update zh-cn keys + replace hardcoded English in templates"""
import glob, re, sys
sys.stdout.reconfigure(encoding='utf-8')

# Step 1: Update zh-cn.ts with missing keys (match en.ts)
zh_path = "src/i18n/pages/opsflow/zh-cn.ts"
with open(zh_path, "r", encoding="utf-8") as f:
    zh = f.read()

# Add missing keys to properties section
zh = zh.replace(
    "properties: {\n        basic: '基本属性',",
    """properties: {
        basic: '基本属性',
        basicInfo: '基本信息',
        label: '标签',"""
)
zh = zh.replace(
    "retryCount: '重试次数',",
    """retryCount: '重试次数',
        retryDelay: '重试间隔(秒)',"""
)
zh = zh.replace(
    "pluginConfig: '插件配置',",
    """pluginConfig: '插件配置',
        actionConfig: '动作配置',
        executionControl: '执行控制',
        subprocessConfig: '子流程配置',
        approvalConfig: '审批配置',
        version: '版本',
        plugin: '插件',
        riskLevel: '风险等级',
        maxRetries: '最大重试次数',
        timeoutSeconds: '超时(秒)',
        optional: '可选',
        targetTemplate: '目标模板',
        variableMapping: '变量映射 (父→子)',
        outputMapping: '输出映射 (子→父)',
        approvers: '审批人',
        mode: '模式',
        independent: '独立',
        embedded: '嵌入',
        outputParams: '输出参数',
        variableRefs: '变量引用',
        reference: '引用',"""
)

with open(zh_path, "w", encoding="utf-8") as f:
    f.write(zh)
print("[OK] zh-cn.ts updated with missing keys")

# Step 2: Define template text -> i18n key mapping
TEMPLATE_REPLACE = {
    # Execution Detail
    "Back": "$t('message.common.back')",
    "Start": "$t('message.execution.start')",
    "Execution Detail": "$t('message.execution.detail')",
    "Node Log": "$t('message.execution.nodeLog')",
    "Node Output": "$t('message.execution.nodeOutput')",
    "Logs": "$t('message.execution.logs')",
    "Output": "$t('message.execution.output')",
    "Traces": "$t('message.execution.traces')",
    "No Logs": "$t('message.execution.noLogs')",
    "No Output": "$t('message.execution.noOutput')",
    "Pending": "$t('message.execution.statusPending')",
    "Running": "$t('message.execution.statusRunning')",
    "Completed": "$t('message.execution.statusFinished')",
    "Failed": "$t('message.execution.statusFailed')",
    "Cancelled": "$t('message.execution.statusCancelled')",
    "Skipped": "$t('message.execution.statusSkipped')",
    "Paused": "$t('message.execution.statusPaused')",
    "Pending Approval": "$t('message.execution.statusPending')",
    "Publish Required": "$t('message.canvas.publishRequired')",
    "Publish": "$t('message.canvas.publish')",
    "Cancel": "$t('message.common.cancel')",
    "Save": "$t('message.common.save')",
    "Delete": "$t('message.common.delete')",
    "Edit": "$t('message.common.edit')",
    "Search": "$t('message.common.search')",
    "Refresh": "$t('message.common.refresh')",
    "Confirm": "$t('message.common.confirm')",
    "Close": "$t('message.common.close')",
    "Loading...": "$t('message.common.loading')",
    "Save Condition": "$t('message.condition.save')",
    "Add Condition": "$t('message.condition.addCondition')",
    "Node Properties": "$t('message.properties.basic')",
    "Basic Info": "$t('message.properties.basicInfo')",
    "Action Config": "$t('message.properties.actionConfig')",
    "Execution Control": "$t('message.properties.executionControl')",
    "SubProcess Config": "$t('message.properties.subprocessConfig')",
    "Approval Config": "$t('message.properties.approvalConfig')",
    "Output Parameters": "$t('message.properties.outputParams')",
    "Variable References": "$t('message.properties.variableRefs')",
    "Select...": "$t('message.common.select')",
    "Version": "$t('message.properties.version')",
    "Max Retries": "$t('message.properties.maxRetries')",
    "Retry Delay (s)": "$t('message.properties.retryDelay')",
    "Timeout (s)": "$t('message.properties.timeoutSeconds')",
    "Risk Level": "$t('message.properties.riskLevel')",
    "Optional": "$t('message.properties.optional')",
    "Label": "$t('message.properties.label')",
    "Target Template": "$t('message.properties.targetTemplate')",
    "Mode": "$t('message.properties.mode')",
    "Independent": "$t('message.properties.independent')",
    "Embedded": "$t('message.properties.embedded')",
    "Approver(s)": "$t('message.properties.approvers')",
    "Variable Mapping (parent → child)": "$t('message.properties.variableMapping')",
    "Output Mapping (child → parent)": "$t('message.properties.outputMapping')",
    "All Categories": "$t('message.plugin.allCategories')",
    "Category": "$t('message.plugin.category')",
    "Description": "$t('message.plugin.description')",
    "Author": "$t('message.plugin.author')",
    "Select Plugin": "$t('message.plugin.selectPlugin')",
    "AI Design": "$t('message.ai.title')",
    "Quick start guide": "$t('message.ai.quickStart')",
    "Ask me anything...": "$t('message.ai.placeholder')",
    "Send": "$t('message.common.send')",
    "No Data": "$t('message.common.noData')",
    "Select approvers": "$t('message.properties.selectApprovers')",
    "No templates yet": "$t('message.template.noTemplates')",
    "Search templates...": "$t('message.template.searchPlaceholder')",
    "Template Name": "$t('message.template.templateName')",
    "Template Description": "$t('message.template.templateDesc')",
    "Template Tag": "$t('message.template.templateTag')",
    "AI Assistant": "$t('message.ai.title')",
    "Projects": "$t('message.project.title')",
    "All Projects": "$t('message.project.allProjects')",
    "Plugins": "$t('message.plugin.title')",
    "All Categories": "$t('message.plugin.allCategories')",
    "Schedules": "$t('message.schedule.title')",
    "Templates": "$t('message.template.title')",
    "Pipeline Design": "$t('message.opsflow.design')",
    "OpsFlow": "$t('message.opsflow.title')",
    "Reference": "$t('message.properties.reference')",
    "Plugin": "$t('message.properties.plugin')",
    "Save Draft": "$t('message.common.save')",
    "Publish": "$t('message.canvas.publish')",
    "Zoom In": "$t('message.canvas.zoomIn')",
    "Zoom Out": "$t('message.canvas.zoomOut')",
    "Auto Layout": "$t('message.canvas.autoLayout')",
    "Full Screen": "$t('message.canvas.fullscreen')",
    "Reset Zoom": "$t('message.canvas.resetZoom')",
    "Undo": "$t('message.canvas.undo')",
    "Redo": "$t('message.canvas.redo')",
    "Copy": "$t('message.canvas.copy')",
    "Paste": "$t('message.canvas.paste')",
    "Select All": "$t('message.canvas.selectAll')",
    "New Template": "$t('message.template.newTemplate')",
    "New Schedule": "$t('message.schedule.newSchedule')",
    "Edit Schedule": "$t('message.schedule.editSchedule')",
    "Delete Schedule": "$t('message.schedule.deleteSchedule')",
    "Schedule Name": "$t('message.schedule.scheduleName')",
    "Cron Expression": "$t('message.schedule.cronExpr')",
    "Trigger Type": "$t('message.schedule.triggerType')",
    "Cron": "$t('message.schedule.cronTrigger')",
    "Interval": "$t('message.schedule.intervalTrigger')",
    "One-time": "$t('message.schedule.onceTrigger')",
    "Enabled": "$t('message.schedule.enabled')",
    "Disabled": "$t('message.schedule.disabled')",
    "Last Run": "$t('message.schedule.lastRun')",
    "Next Run": "$t('message.schedule.nextRun')",
    "Run Count": "$t('message.schedule.runCount')",
}

# Also add these missing keys to en.ts and zh-cn.ts
en_path = "src/i18n/pages/opsflow/en.ts"
with open(en_path, "r", encoding="utf-8") as f:
    en = f.read()

# These keys need to be added to execution section
en_additions = {
    "start": "'Start'",
    "logs": "'Logs'",
    "traces": "'Traces'",
    "output": "'Output'",
    "noLogs": "'No Logs'",
    "noOutput": "'No Output'",
}

# Add to execution section
exec_end = en.index("retrySuccess: 'Retry successful'")
en = en[:exec_end] + "\n".join(f"        {k}: {v}," for k, v in en_additions.items()) + "\n" + en[exec_end:]

with open(en_path, "w", encoding="utf-8") as f:
    f.write(en)
print("[OK] en.ts updated with execution keys")

# Same for zh-cn.ts
zh_additions = {
    "start": "'启动'",
    "logs": "'日志'",
    "traces": "'追踪'",
    "output": "'输出'",
    "noLogs": "'暂无日志'",
    "noOutput": "'暂无输出'",
}

with open(zh_path, "r", encoding="utf-8") as f:
    zh = f.read()

exec_end_zh = zh.index("retrySuccess: '重试成功'")
zh = zh[:exec_end_zh] + "\n".join(f"        {k}: '{v}'," for k, v in zh_additions.items()) + "\n" + zh[exec_end_zh:]

with open(zh_path, "w", encoding="utf-8") as f:
    f.write(zh)
print("[OK] zh-cn.ts updated with execution keys")

# Step 3: Replace template text in all .vue files
vue_files = []
for p in ["src/views/apps/opsflow/**/*.vue", "src/views/apps/opsflow-execution/**/*.vue"]:
    vue_files.extend(glob.glob(f"src/{p}", recursive=True))

total_replaced = 0
for fp in sorted(vue_files):
    with open(fp, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    orig = content

    # Find the template section
    template_match = re.search(r'<template>(.*?)</template>', content, re.DOTALL)
    if not template_match:
        continue

    template = template_match.group(1)
    new_template = template

    # Sort by length descending to avoid partial matches
    for text, replacement in sorted(TEMPLATE_REPLACE.items(), key=lambda x: -len(x[0])):
        # Only replace standalone text between HTML tags
        # Pattern: text between > and <
        old_pattern = re.escape(text)
        # Replace >text< with >$t(...)<
        new_template = re.sub(
            rf'(?<=>){old_pattern}(?=<)',
            lambda m: replacement if m.group(0) == text else m.group(0),
            new_template
        )
        # Also handle text inside {{ }} that isn't already a $t call
        new_template = re.sub(
            rf'{{{{\s*[\'"]{old_pattern}[\'"]\s*}}}}',
            replacement,
            new_template
        )

    if new_template != template:
        content = content.replace(template, new_template)
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        total_replaced += 1

print(f"[OK] Updated {total_replaced} .vue files with template i18n replacements")

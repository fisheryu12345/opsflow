#!/usr/bin/env python
"""Redo SubmitWizardDialog i18n - template section only (safe approach)"""
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

fp = 'src/views/apps/opsflow/components/dialogs/SubmitWizardDialog.vue'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()
orig = content

# Split template from script
tmpl_match = re.search(r'(<template>)(.*?)(</template>)', content, re.DOTALL)
before = content[:tmpl_match.start(2)]
tmpl = tmpl_match.group(2)
after = content[tmpl_match.end(2):]

# === Template section replacements ===
# Attribute bindings
tmpl = tmpl.replace('title="Submit Execution Wizard"', ':title="$t(\'message.wizard.title\')"')
tmpl = tmpl.replace('placeholder="Search change requests..."', ':placeholder="$t(\'message.wizard.searchCr\')"')
tmpl = tmpl.replace('placeholder="Select date"', ':placeholder="$t(\'message.wizard.selectDate\')"')
tmpl = tmpl.replace('placeholder="Select time"', ':placeholder="$t(\'message.wizard.selectTime\')"')

# Text content - only text between HTML tags (safe: no JS identifiers in template)
text_map = {
    'Pipeline Validation': '{{ $t("message.wizard.validation") }}',
    'Validate topology, node configuration, and engine compatibility': '{{ $t("message.wizard.validationDesc") }}',
    'Nodes': '{{ $t("message.wizard.nodes") }}',
    'Edges': '{{ $t("message.wizard.edges") }}',
    'Atom Types': '{{ $t("message.wizard.atomTypes") }}',
    'Run Validation': '{{ $t("message.wizard.runValidation") }}',
    'AI analyzes pipeline structure for compliance': '{{ $t("message.wizard.validationHint") }}',
    'Validation Passed': '{{ $t("message.wizard.validationPassed") }}',
    'Topology is complete, no orphan nodes, gateway paths correct, Bamboo engine compatible': '{{ $t("message.wizard.validationPassedDesc") }}',
    'Warning': '{{ $t("message.wizard.warning") }}',
    'Error': '{{ $t("message.wizard.error") }}',
    'Link Change Request': '{{ $t("message.wizard.linkChange") }}',
    'Select the change request associated with this pipeline': '{{ $t("message.wizard.linkChangeDesc") }}',
    'Change Request Details': '{{ $t("message.wizard.crDetails") }}',
    'CR Number': '{{ $t("message.wizard.crNumber") }}',
    'Change Window': '{{ $t("message.wizard.changeWindow") }}',
    'Requester': '{{ $t("message.wizard.requester") }}',
    'Description': '{{ $t("message.wizard.description") }}',
    'Parameters & Variables': '{{ $t("message.wizard.paramsVars") }}',
    'Override template variable defaults for this execution': '{{ $t("message.wizard.paramsVarsDesc") }}',
    'No parameters defined in this template': '{{ $t("message.wizard.noParams") }}',
    'AI Risk Analysis & Confirmation': '{{ $t("message.wizard.riskAnalysis") }}',
    'Review change impact and acknowledge each risk item': '{{ $t("message.wizard.riskAnalysisDesc") }}',
    'Execute Risk Analysis': '{{ $t("message.wizard.executeRisk") }}',
    'AI analyzes change impact and identifies risks': '{{ $t("message.wizard.riskHint") }}',
    'Change Summary': '{{ $t("message.wizard.changeSummary") }}',
    'Schedule Strategy': '{{ $t("message.wizard.scheduleStrategy") }}',
    'Set execution timing after approval': '{{ $t("message.wizard.scheduleStrategyDesc") }}',
    'Scheduled Execution': '{{ $t("message.wizard.scheduledExecution") }}',
    'Auto-execute at a specified time after approval': '{{ $t("message.wizard.scheduledDesc") }}',
    'Manual Trigger': '{{ $t("message.wizard.manualTrigger") }}',
    'Manually start after ServiceNow approval completes': '{{ $t("message.wizard.manualDesc") }}',
    'Pick Execution Time': '{{ $t("message.wizard.pickTime") }}',
    'Manual Execution': '{{ $t("message.wizard.manualExecution") }}',
    '← Back': '← {{ $t("message.wizard.back") }}',
    'Submit Execution': '{{ $t("message.wizard.submitExecution") }}',
}

# Sort by length descending to avoid partial matches
for old in sorted(text_map.keys(), key=len, reverse=True):
    if old in tmpl:
        tmpl = tmpl.replace(old, text_map[old])

# UI labels (generic words used as labels in template, NOT in JS)
# Only replace when they appear between > and < or in element content
for word, key in [
    ('Date', 'date'), ('Time', 'time'), ('Status', 'status'), ('Title', 'title'),
]:
    # Match word between HTML tags
    tmpl = re.sub(
        rf'(?<=>){word}(?=<)',
        f'{{{{ $t("message.wizard.{key}") }}}}',
        tmpl
    )

# Cancel button text
tmpl = re.sub(r'(?<=>)\s*Cancel\s*(?=<)', '{{ $t("message.wizard.cancel") }}', tmpl)

# Continue button
tmpl = tmpl.replace('Continue →', '{{ $t("message.wizard.continue") }} →')

# CR status badges
tmpl = tmpl.replace(
    "cr.status === 'approved' ? 'Approved' : 'Pending'",
    "cr.status === 'approved' ? $t('message.wizard.approved') : $t('message.wizard.pending')"
)
tmpl = tmpl.replace(
    "selectedCr.status === 'approved' ? 'Approved' : 'Pending'",
    "selectedCr.status === 'approved' ? $t('message.wizard.approved') : $t('message.wizard.pending')"
)

# Risk level badges
tmpl = tmpl.replace(
    "risk.level === 'high' ? 'High' : risk.level === 'medium' ? 'Medium' : 'Low'",
    "risk.level === 'high' ? $t('message.wizard.high') : risk.level === 'medium' ? $t('message.wizard.medium') : $t('message.wizard.low')"
)

# Risk items title
tmpl = tmpl.replace('Risk Items — acknowledge each to proceed', '{{ $t("message.wizard.riskItems") }}')

# Acknowledge text
old_ack = '<strong>I acknowledge all risks above</strong> and confirm this execution. I assume responsibility for any unlisted risks.'
new_ack = '<strong>{{ $t("message.wizard.acknowledgeAll") }}</strong>'
if old_ack in tmpl:
    tmpl = tmpl.replace(old_ack, new_ack)

# Change window display
old_cw = 'Change window: <strong>{{ selectedCr.change_window_start }}</strong> ~ <strong>{{ selectedCr.change_window_end }}</strong> · Available: <strong>{{ windowStart }}</strong> ~ <strong>{{ windowEndExclusive }}</strong>'
new_cw = '{{ $t("message.wizard.changeWindowRange", { start: selectedCr.change_window_start, end: selectedCr.change_window_end, availStart: windowStart, availEnd: windowEndExclusive }) }}'
if old_cw in tmpl:
    tmpl = tmpl.replace(old_cw, new_cw)

# Auto-cancel warning
old_ac = 'If not approved <strong>30 minutes</strong> before the scheduled time, this plan <strong>auto-cancels</strong>. Ensure timely approval.'
new_ac = '{{ $t("message.wizard.autoCancelWarning") }}'
tmpl = tmpl.replace(old_ac, new_ac)

# Manual execution description
old_me = 'Creates an Execution with status <code>pending_approval</code>. After ServiceNow approves the change, you can manually start it from the Executions page.'
new_me = '{{ $t("message.wizard.manualExecutionDesc") }}'
tmpl = tmpl.replace(old_me, new_me)

# Suggestions
tmpl = tmpl.replace('\U0001f4a1 Suggestions', '{{ $t("message.wizard.suggestions") }}')

# Rebuild
content = before + tmpl + after

# === Script section: minimal, targeted replacements ===
content = content.replace(
    "{ title: 'Validation', desc: 'Pipeline Check' },",
    "{ title: t('message.wizard.step1Title'), desc: t('message.wizard.step1Desc') },"
)
content = content.replace(
    "{ title: 'Change', desc: 'Link Change Request' },",
    "{ title: t('message.wizard.step2Title'), desc: t('message.wizard.step2Desc') },"
)
content = content.replace(
    "{ title: 'Params', desc: 'Variables' },",
    "{ title: t('message.wizard.step3Title'), desc: t('message.wizard.step3Desc') },"
)
content = content.replace(
    "{ title: 'Risk', desc: 'AI Analysis & Confirm' },",
    "{ title: t('message.wizard.step4Title'), desc: t('message.wizard.step4Desc') },"
)
content = content.replace(
    "{ title: 'Schedule', desc: 'Timing Strategy' },",
    "{ title: t('message.wizard.step5Title'), desc: t('message.wizard.step5Desc') },"
)

# Var type labels
content = content.replace(
    "var m: Record<string, string> = { input: 'Text', textarea: 'Textarea', password: 'Password', int: 'Number', float: 'Float' }",
    "var m: Record<string, string> = { input: t('message.wizard.text'), textarea: t('message.wizard.textarea'), password: t('message.wizard.password'), int: t('message.wizard.number'), float: t('message.wizard.float') }"
)

content = content.replace(
    "return 'Enter value...'",
    "return t('message.wizard.enterValue')"
)

# Error messages
content = content.replace("e?.msg || e?.message || 'Validation failed'",
                          "e?.msg || e?.message || t('message.wizard.validationFailed')")
content = content.replace("e?.msg || e?.message || 'Risk analysis failed'",
                          "e?.msg || e?.message || t('message.wizard.riskAnalysisFailed')")
content = content.replace("errMsg = e?.response?.data?.msg || e?.msg || e?.message || 'Submission failed'",
                          "errMsg = e?.response?.data?.msg || e?.msg || e?.message || t('message.wizard.submissionFailed')")

# Success messages
content = content.replace(
    '? `Execution #${execId} created (ready to start).`',
    "? t('message.wizard.execCreated', { id: execId })"
)
content = content.replace(
    ': `Execution #${execId} created (pending_approval). Start it manually after ServiceNow approval.`',
    ": t('message.wizard.execCreatedPending', { id: execId })"
)
content = content.replace(
    '? `Execution #${execId} created. Scheduled at ${scheduledDate.value} ${scheduledTime.value}.`',
    "? t('message.wizard.execScheduled', { id: execId, date: scheduledDate.value, time: scheduledTime.value })"
)
content = content.replace(
    ': `Execution #${execId} created. Schedule set for ${scheduledDate.value} ${scheduledTime.value}. Auto-cancels if not approved 30min before.`',
    ": t('message.wizard.execScheduledPending', { id: execId, date: scheduledDate.value, time: scheduledTime.value })"
)

with open(fp, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify: no JS identifier corruption
script_match = re.search(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
if script_match:
    script = script_match.group(1)
    corrupted = re.findall(r'\b(pipeline|atom|scheduled|disabled|riskChecked|step|varTypeLabel)\{\{ \$t\(', script)
    if corrupted:
        print(f'ERROR: {len(corrupted)} corrupted variables in script!')
        for c in corrupted: print(f'  {c}')
    else:
        print('OK: No script corruption')

# Verify no pipelineNodes/pipelineEdges corrupted in template
if 'pipeline{{ $t' in content:
    print('ERROR: pipelineNodes/pipelineEdges still corrupted!')
else:
    print('OK: pipeline var names intact')

print(f'Total length: {len(content)} chars')
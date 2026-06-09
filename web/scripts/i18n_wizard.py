#!/usr/bin/env python
"""Replace hardcoded English in SubmitWizardDialog.vue with $t() calls"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

fp = 'src/views/apps/opsflow/components/dialogs/SubmitWizardDialog.vue'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

orig = content

# --- Template text replacements ---
pairs = [
    ('title="Submit Execution Wizard"', ':title="$t(\'message.wizard.title\')"'),
    ('Pipeline Validation', '{{ $t("message.wizard.validation") }}'),
    ('Validate topology, node configuration, and engine compatibility', '{{ $t("message.wizard.validationDesc") }}'),
    ('Nodes', '{{ $t("message.wizard.nodes") }}'),
    ('Edges', '{{ $t("message.wizard.edges") }}'),
    ('Atom Types', '{{ $t("message.wizard.atomTypes") }}'),
    ('Run Validation', '{{ $t("message.wizard.runValidation") }}'),
    ('AI analyzes pipeline structure for compliance', '{{ $t("message.wizard.validationHint") }}'),
    ('Validation Passed', '{{ $t("message.wizard.validationPassed") }}'),
    ('Topology is complete, no orphan nodes, gateway paths correct, Bamboo engine compatible', '{{ $t("message.wizard.validationPassedDesc") }}'),
    ('Warning', '{{ $t("message.wizard.warning") }}'),
    ('Error', '{{ $t("message.wizard.error") }}'),
    ('Link Change Request', '{{ $t("message.wizard.linkChange") }}'),
    ('Select the change request associated with this pipeline', '{{ $t("message.wizard.linkChangeDesc") }}'),
    ('Search change requests...', '{{ $t("message.wizard.searchCr") }}'),
    ('Change Request Details', '{{ $t("message.wizard.crDetails") }}'),
    ('CR Number', '{{ $t("message.wizard.crNumber") }}'),
    ('Change Window', '{{ $t("message.wizard.changeWindow") }}'),
    ('Requester', '{{ $t("message.wizard.requester") }}'),
    ('Description', '{{ $t("message.wizard.description") }}'),
    ('Parameters & Variables', '{{ $t("message.wizard.paramsVars") }}'),
    ('Override template variable defaults for this execution', '{{ $t("message.wizard.paramsVarsDesc") }}'),
    ('No parameters defined in this template', '{{ $t("message.wizard.noParams") }}'),
    ('AI Risk Analysis & Confirmation', '{{ $t("message.wizard.riskAnalysis") }}'),
    ('Review change impact and acknowledge each risk item', '{{ $t("message.wizard.riskAnalysisDesc") }}'),
    ('Execute Risk Analysis', '{{ $t("message.wizard.executeRisk") }}'),
    ('AI analyzes change impact and identifies risks', '{{ $t("message.wizard.riskHint") }}'),
    ('Change Summary', '{{ $t("message.wizard.changeSummary") }}'),
    ('Schedule Strategy', '{{ $t("message.wizard.scheduleStrategy") }}'),
    ('Set execution timing after approval', '{{ $t("message.wizard.scheduleStrategyDesc") }}'),
    ('Scheduled Execution', '{{ $t("message.wizard.scheduledExecution") }}'),
    ('Auto-execute at a specified time after approval', '{{ $t("message.wizard.scheduledDesc") }}'),
    ('Manual Trigger', '{{ $t("message.wizard.manualTrigger") }}'),
    ('Manually start after ServiceNow approval completes', '{{ $t("message.wizard.manualDesc") }}'),
    ('Pick Execution Time', '{{ $t("message.wizard.pickTime") }}'),
    ('Date', '{{ $t("message.wizard.date") }}'),
    ('Time', '{{ $t("message.wizard.time") }}'),
    ('Select date', '{{ $t("message.wizard.selectDate") }}'),
    ('Select time', '{{ $t("message.wizard.selectTime") }}'),
    ('Manual Execution', '{{ $t("message.wizard.manualExecution") }}'),
]

for old, new in pairs:
    if old in content:
        content = content.replace(old, new)

# --- Complex replacements ---
# Risk items title (has em dash)
content = content.replace('Risk Items — acknowledge each to proceed', '{{ $t("message.wizard.riskItems") }}')

# I acknowledge text block
old_ack = '<span class="risk-confirm-text">\n                      <strong>I acknowledge all risks above</strong> and confirm this execution. I assume responsibility for any unlisted risks.\n                    </span>'
new_ack = '<span class="risk-confirm-text">\n                      {{ $t("message.wizard.acknowledgeAll") }}\n                    </span>'
if old_ack in content:
    content = content.replace(old_ack, new_ack)
elif 'I acknowledge all risks above' in content:
    # Fallback: simpler match
    content = content.replace(
        '<strong>I acknowledge all risks above</strong> and confirm this execution. I assume responsibility for any unlisted risks.',
        '{{ $t("message.wizard.acknowledgeAll") }}'
    )

# Risk level badges (ternary in template)
old_risk = "risk.level === 'high' ? 'High' : risk.level === 'medium' ? 'Medium' : 'Low'"
new_risk = "risk.level === 'high' ? $t('message.wizard.high') : risk.level === 'medium' ? $t('message.wizard.medium') : $t('message.wizard.low')"
if old_risk in content:
    content = content.replace(old_risk, new_risk)

# CR status badges
for old, new in [
    ("cr.status === 'approved' ? 'Approved' : 'Pending'",
     "cr.status === 'approved' ? $t('message.wizard.approved') : $t('message.wizard.pending')"),
    ("selectedCr.status === 'approved' ? 'Approved' : 'Pending'",
     "selectedCr.status === 'approved' ? $t('message.wizard.approved') : $t('message.wizard.pending')"),
]:
    if old in content:
        content = content.replace(old, new)

# Steps definition (in script)
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

# Enter value
content = content.replace("return 'Enter value...'", "return t('message.wizard.enterValue')")

# Error messages
content = content.replace("e?.msg || e?.message || 'Validation failed'", "e?.msg || e?.message || t('message.wizard.validationFailed')")
content = content.replace("e?.msg || e?.message || 'Risk analysis failed'", "e?.msg || e?.message || t('message.wizard.riskAnalysisFailed')")
content = content.replace("e?.msg || e?.message || 'Submission failed'", "e?.msg || e?.message || t('message.wizard.submissionFailed')")
content = content.replace("errMsg = e?.response?.data?.msg || e?.msg || e?.message || 'Submission failed'",
                          "errMsg = e?.response?.data?.msg || e?.msg || e?.message || t('message.wizard.submissionFailed')")

# Change window display
old_window = 'Change window: <strong>{{ selectedCr.change_window_start }}</strong> ~ <strong>{{ selectedCr.change_window_end }}</strong> · Available: <strong>{{ windowStart }}</strong> ~ <strong>{{ windowEndExclusive }}</strong>'
new_window = '{{ $t("message.wizard.changeWindowRange", { start: selectedCr.change_window_start, end: selectedCr.change_window_end, availStart: windowStart, availEnd: windowEndExclusive }) }}'
if old_window in content:
    content = content.replace(old_window, new_window)

# Auto-cancel warning
old_cancel = 'If not approved <strong>30 minutes</strong> before the scheduled time, this plan <strong>auto-cancels</strong>. Ensure timely approval.'
new_cancel = '{{ $t("message.wizard.autoCancelWarning") }}'
if old_cancel in content:
    content = content.replace(old_cancel, new_cancel)

# Manual execution description
old_manual = 'Creates an Execution with status <code>pending_approval</code>. After ServiceNow approves the change, you can manually start it from the Executions page.'
new_manual = '{{ $t("message.wizard.manualExecutionDesc") }}'
if old_manual in content:
    content = content.replace(old_manual, new_manual)

# Success messages - ECMAScript template literals with backticks
old_success1 = '? `Execution #${execId} created (ready to start).`'
new_success1 = '? t(\'message.wizard.execCreated\', { id: execId })'
if old_success1 in content:
    content = content.replace(old_success1, new_success1)

old_success2 = ': `Execution #${execId} created (pending_approval). Start it manually after ServiceNow approval.`'
new_success2 = ': t(\'message.wizard.execCreatedPending\', { id: execId })'
if old_success2 in content:
    content = content.replace(old_success2, new_success2)

old_success3 = '? `Execution #${execId} created. Scheduled at ${scheduledDate.value} ${scheduledTime.value}.`'
new_success3 = '? t(\'message.wizard.execScheduled\', { id: execId, date: scheduledDate.value, time: scheduledTime.value })'
if old_success3 in content:
    content = content.replace(old_success3, new_success3)

old_success4 = ': `Execution #${execId} created. Schedule set for ${scheduledDate.value} ${scheduledTime.value}. Auto-cancels if not approved 30min before.`'
new_success4 = ': t(\'message.wizard.execScheduledPending\', { id: execId, date: scheduledDate.value, time: scheduledTime.value })'
if old_success4 in content:
    content = content.replace(old_success4, new_success4)

# Navigation buttons
content = content.replace('← Back', '← {{ $t("message.wizard.back") }}')

# Fix: Title key conflict - "Title" in CR section was already replaced above
# But we need to make sure the generic text 'Title' used only in CR context
# is handled correctly
content = content.replace('<div class=\"section-title\">Title</div>',
                          '<div class=\"section-title\">{{ $t(\"message.wizard.title\") }}</div>')

# ElMessage empty text
content = content.replace('No parameters defined in this template',
                          '{{ $t("message.wizard.noParams") }}')

# Suggestions section
content = content.replace('💡 Suggestions', '{{ $t("message.wizard.suggestions") }}')

# Write back
if content != orig:
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SubmitWizardDialog.vue: updated')
else:
    print('SubmitWizardDialog.vue: no changes')

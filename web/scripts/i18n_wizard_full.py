#!/usr/bin/env python
"""Full i18n conversion for SubmitWizardDialog.vue"""
import sys, re, json
sys.stdout.reconfigure(encoding='utf-8')

fp = 'src/views/apps/opsflow/components/dialogs/SubmitWizardDialog.vue'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()
orig = content

# Add imports
content = content.replace(
    "import { ref, computed, watch } from 'vue'",
    "import { ref, computed, watch } from 'vue'\nimport { useI18n } from 'vue-i18n'"
)

# Add t() after defineEmits
content = content.replace(
    "}()\n\n// ---------- Dialog State ----------",
    "}()\nconst { t } = useI18n()\n\n// ---------- Dialog State ----------"
)

# Title
content = content.replace('title="Submit Execution Wizard"', ':title="$t(\'message.wizard.title\')"')

# ===== Template text replacements =====
# Step 1 - Validation
content = content.replace('<h3>Pipeline Validation</h3>', '<h3>{{ $t("message.wizard.validation") }}</h3>')
content = content.replace('<p>Validate topology, node configuration, and engine compatibility</p>',
    '<p>{{ $t("message.wizard.validationDesc") }}</p>')
content = content.replace('<div class="metric-label">Nodes</div>', '<div class="metric-label">{{ $t("message.wizard.nodes") }}</div>')
content = content.replace('<div class="metric-label">Edges</div>', '<div class="metric-label">{{ $t("message.wizard.edges") }}</div>')
content = content.replace('<div class="metric-label">Atom Types</div>', '<div class="metric-label">{{ $t("message.wizard.atomTypes") }}</div>')
content = content.replace('>Run Validation<', '>{{ $t("message.wizard.runValidation") }}<')
content = content.replace('AI analyzes pipeline structure for compliance', '{{ $t("message.wizard.validationHint") }}')
content = content.replace('Validation Passed', '{{ $t("message.wizard.validationPassed") }}')
content = content.replace('Topology is complete, no orphan nodes, gateway paths correct, Bamboo engine compatible',
    '{{ $t("message.wizard.validationPassedDesc") }}')
content = content.replace('Warning', '{{ $t("message.wizard.warning") }}')
content = content.replace('Error', '{{ $t("message.wizard.error") }}')

# Step 2 - Change Request
content = content.replace('<h3>Link Change Request</h3>', '<h3>{{ $t("message.wizard.linkChange") }}</h3>')
content = content.replace('<p>Select the change request associated with this pipeline</p>',
    '<p>{{ $t("message.wizard.linkChangeDesc") }}</p>')
content = content.replace('placeholder="Search change requests..."', ':placeholder="$t(\'message.wizard.searchCr\')"')
content = content.replace('>Change Request Details<', '>{{ $t("message.wizard.crDetails") }}<')
content = content.replace('CR Number', '{{ $t("message.wizard.crNumber") }}')
content = content.replace('Change Window', '{{ $t("message.wizard.changeWindow") }}')
content = content.replace('Requester', '{{ $t("message.wizard.requester") }}')
content = content.replace('Description', '{{ $t("message.wizard.description") }}')

# Step 3 - Parameters
content = content.replace('<h3>Parameters &amp; Variables</h3>', '<h3>{{ $t("message.wizard.paramsVars") }}</h3>')
content = content.replace('<p>Override template variable defaults for this execution</p>',
    '<p>{{ $t("message.wizard.paramsVarsDesc") }}</p>')
content = content.replace('No parameters defined in this template', '{{ $t("message.wizard.noParams") }}')

# Step 4 - Risk
content = content.replace('<h3>AI Risk Analysis &amp; Confirmation</h3>', '<h3>{{ $t("message.wizard.riskAnalysis") }}</h3>')
content = content.replace('<p>Review change impact and acknowledge each risk item</p>',
    '<p>{{ $t("message.wizard.riskAnalysisDesc") }}</p>')
content = content.replace('>Execute Risk Analysis<', '>{{ $t("message.wizard.executeRisk") }}<')
content = content.replace('AI analyzes change impact and identifies risks', '{{ $t("message.wizard.riskHint") }}')
content = content.replace('Change Summary', '{{ $t("message.wizard.changeSummary") }}')

# Step 5 - Schedule
content = content.replace('<h3>Schedule Strategy</h3>', '<h3>{{ $t("message.wizard.scheduleStrategy") }}</h3>')
content = content.replace('<p>Set execution timing after approval</p>',
    '<p>{{ $t("message.wizard.scheduleStrategyDesc") }}</p>')
content = content.replace('Scheduled Execution', '{{ $t("message.wizard.scheduledExecution") }}')
content = content.replace('Auto-execute at a specified time after approval', '{{ $t("message.wizard.scheduledDesc") }}')
content = content.replace('Manual Trigger', '{{ $t("message.wizard.manualTrigger") }}')
content = content.replace('Manually start after ServiceNow approval completes', '{{ $t("message.wizard.manualDesc") }}')
content = content.replace('Pick Execution Time', '{{ $t("message.wizard.pickTime") }}')

# Suggestions header
content = content.replace('💡 Suggestions', '{{ $t("message.wizard.suggestions") }}')

# Risk Items title
content = content.replace('Risk Items — acknowledge each to proceed', '{{ $t("message.wizard.riskItems") }}')

# Footer buttons
content = content.replace('← Back', '← {{ $t("message.wizard.back") }}')
content = content.replace('>Cancel<', '>{{ $t("message.wizard.cancel") }}<')
content = content.replace('Continue →', '{{ $t("message.wizard.continue") }} →')
content = content.replace('>Submit Execution<', '>{{ $t("message.wizard.submitExecution") }}<')

# Navigation buttons (el-button text)
content = content.replace('>Back<', '>{{ $t("message.wizard.back") }}<')

# CR status badges
content = content.replace(
    "cr.status === 'approved' ? 'Approved' : 'Pending'",
    "cr.status === 'approved' ? $t('message.wizard.approved') : $t('message.wizard.pending')"
)
content = content.replace(
    "selectedCr.status === 'approved' ? 'Approved' : 'Pending'",
    "selectedCr.status === 'approved' ? $t('message.wizard.approved') : $t('message.wizard.pending')"
)

# Risk level badges
content = content.replace(
    "risk.level === 'high' ? 'High' : risk.level === 'medium' ? 'Medium' : 'Low'",
    "risk.level === 'high' ? $t('message.wizard.high') : risk.level === 'medium' ? $t('message.wizard.medium') : $t('message.wizard.low')"
)

# Acknowledge text
content = content.replace(
    '<strong>I acknowledge all risks above</strong> and confirm this execution. I assume responsibility for any unlisted risks.',
    '{{ $t("message.wizard.acknowledgeAll") }}'
)

# ElMessage texts
content = content.replace("'Validation failed'", "t('message.wizard.validationFailed')")
content = content.replace("'Risk analysis failed'", "t('message.wizard.riskAnalysisFailed')")
content = content.replace("'Submission failed'", "t('message.wizard.submissionFailed')")

# Steps definition
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

# Enter value placeholder
content = content.replace("return 'Enter value...'", "return t('message.wizard.enterValue')")

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

# Change window display and auto-cancel warning
content = content.replace(
    'Change window: <strong>{{ selectedCr.change_window_start }}</strong> ~ <strong>{{ selectedCr.change_window_end }}</strong> · Available: <strong>{{ windowStart }}</strong> ~ <strong>{{ windowEndExclusive }}</strong>',
    '{{ $t("message.wizard.changeWindowRange", { start: selectedCr.change_window_start, end: selectedCr.change_window_end, availStart: windowStart, availEnd: windowEndExclusive }) }}'
)
content = content.replace(
    'If not approved <strong>30 minutes</strong> before the scheduled time, this plan <strong>auto-cancels</strong>. Ensure timely approval.',
    '{{ $t("message.wizard.autoCancelWarning") }}'
)
content = content.replace(
    'Creates an Execution with status <code>pending_approval</code>. After ServiceNow approves the change, you can manually start it from the Executions page.',
    '{{ $t("message.wizard.manualExecutionDesc") }}'
)

# Fix hasErrors (must NOT be translated)
content = content.replace('validationResult.hasErrors', 'validationResult.hasErrors')

with open(fp, 'w', encoding='utf-8') as f:
    f.write(content)

print('SubmitWizardDialog.vue: updated')

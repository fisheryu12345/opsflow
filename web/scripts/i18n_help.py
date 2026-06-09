#!/usr/bin/env python
"""Replace hardcoded text in HelpDrawer.vue with $t() calls"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

fp = 'src/views/apps/opsflow/components/common/HelpDrawer.vue'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

orig = content

# Header
content = content.replace('<span>Quick Start Guide</span>',
    '<span>{{ $t("message.helpDrawer.title") }}</span>')
content = content.replace('👉 5-Step Tour',
    '👉 {{ $t("message.helpDrawer.tourBtn") }}')

# Overview
content = content.replace('<h2 class="help-h2">Overview</h2>',
    '<h2 class="help-h2">{{ $t("message.helpDrawer.overview") }}</h2>')
for old, key in [('Create', 'create'), ('Design', 'design'), ('Publish', 'publish'),
                  ('Execute', 'execute'), ('Monitor', 'monitor')]:
    content = content.replace(f'<span>{old}</span>',
        f'<span>{{{{ $t("message.helpDrawer.{key}") }}}}</span>')

# Section titles
sections = [
    ('1. Create Template', 'createTemplate'), ('2. Design Pipeline', 'designPipeline'),
    ('3. Publish Version', 'publishVersion'), ('4. Execution Flow', 'executionFlow'),
    ('5. Monitor & Troubleshoot', 'monitorTitle'),
    ('6. FAQ', 'faq'),
]
for old, key in sections:
    content = content.replace(f'<h2 class="help-h2">{old}</h2>',
        f'<h2 class="help-h2">{{{{ $t("message.helpDrawer.{key}") }}}}</h2>')

# AI Generate
content = content.replace('<strong>AI Generate</strong>',
    '<strong>{{ $t("message.helpDrawer.aiGenerate") }}</strong>')
content = content.replace('<p>Describe your workflow in natural language — AI builds the pipeline</p>',
    '<p>{{ $t("message.helpDrawer.aiGenerateDesc") }}</p>')

# Blank Canvas
content = content.replace('<strong>Blank Canvas</strong>',
    '<strong>{{ $t("message.helpDrawer.blankCanvas") }}</strong>')
content = content.replace('<p>Drag nodes from the Stencil to build manually</p>',
    '<p>{{ $t("message.helpDrawer.blankCanvasDesc") }}</p>')

# Clone
content = content.replace('<strong>Clone Existing</strong>',
    '<strong>{{ $t("message.helpDrawer.cloneExisting") }}</strong>')
content = content.replace('<p>Duplicate an existing template as a starting point</p>',
    '<p>{{ $t("message.helpDrawer.cloneExistingDesc") }}</p>')

# Draft tip
content = content.replace('<strong>💡 Draft vs Published:</strong>',
    '<strong>{{ $t("message.helpDrawer.draftTip") }}</strong>')
content = content.replace('New templates are drafts — editable but non-executable. Publish to create a version snapshot and enable execution.',
    '{{ $t("message.helpDrawer.draftTipDesc") }}')

# Node types
content = content.replace('<span>Start / End</span>',
    '<span>{{ $t("message.helpDrawer.startEnd") }}</span>')
content = content.replace('<span>Task Node <em class="help-warn">plugin required</em></span>',
    '<span>{{ $t("message.helpDrawer.taskNode") }} <em class="help-warn">{{ $t("message.helpDrawer.pluginRequired") }}</em></span>')
content = content.replace('<span>Exclusive Gateway (condition)</span>',
    '<span>{{ $t("message.helpDrawer.exclusiveGateway") }}</span>')
content = content.replace('<span>Parallel Gateway (fan-out)</span>',
    '<span>{{ $t("message.helpDrawer.parallelGateway") }}</span>')
content = content.replace('<span>Converge Gateway (join)</span>',
    '<span>{{ $t("message.helpDrawer.convergeGateway") }}</span>')
content = content.replace('<span>Subprocess (reuse template)</span>',
    '<span>{{ $t("message.helpDrawer.subprocess") }}</span>')

# Key Actions
content = content.replace('<h3 class="help-h3">Key Actions</h3>',
    '<h3 class="help-h3">{{ $t("message.helpDrawer.keyActions") }}</h3>')

# Action items
content = content.replace(
    '<li>Drag nodes from the <strong>Stencil</strong> (left panel) onto the canvas</li>',
    '<li>{{ $t("message.helpDrawer.actionDrag") }}</li>')
content = content.replace(
    '<li>Task nodes <strong>MUST select a plugin</strong> (Shell / Ansible / etc.) or they cannot execute</li>',
    '<li>{{ $t("message.helpDrawer.actionPlugin") }}</li>')
content = content.replace(
    '<li>Select a node → configure parameters, timeout, retry policy in the right Property Panel</li>',
    '<li>{{ $t("message.helpDrawer.actionConfig") }}</li>')

# Action with code
content = content.replace(
    '<li>Variable reference: <code>${node_id.output_key}</code></li>',
    '<li v-html="$t(\'message.helpDrawer.actionVar\', { code: \'${node_id.output_key}\' })"></li>')
content = content.replace(
    '<li>Edge condition: from Exclusive Gateway, set <code>${node_id.key} > 80</code></li>',
    '<li v-html="$t(\'message.helpDrawer.actionEdge\', { code: \'${node_id.key} > 80\' })"></li>')

# Publish items
content = content.replace(
    '<li>Click <strong>Save</strong> in the toolbar to save the draft</li>',
    '<li>{{ $t("message.helpDrawer.pubSave") }}</li>')
content = content.replace(
    '<li>Click <strong>Publish</strong> (or the execution wizard triggers it automatically)</li>',
    '<li>{{ $t("message.helpDrawer.pubPublish") }}</li>')
content = content.replace(
    '<li>Publishing freezes a snapshot — executions always read the snapshot, <strong>live edits are isolated</strong></li>',
    '<li>{{ $t("message.helpDrawer.pubSnapshot") }}</li>')

# Execution flow
content = content.replace(
    '<p>Click <strong>▶ Execute</strong> to open the 5-step submission wizard:</p>',
    '<p>{{ $t("message.helpDrawer.execDesc") }}</p>')
content = content.replace('<div>① AI Validation</div>',
    '<div>{{ $t("message.helpDrawer.execStep1") }}</div>')
content = content.replace('<div>② Link Change Request</div>',
    '<div>{{ $t("message.helpDrawer.execStep2") }}</div>')
content = content.replace('<div>③ Set Variables</div>',
    '<div>{{ $t("message.helpDrawer.execStep3") }}</div>')
content = content.replace('<div>④ Risk Assessment</div>',
    '<div>{{ $t("message.helpDrawer.execStep4") }}</div>')
content = content.replace('<div>⑤ Schedule</div>',
    '<div>{{ $t("message.helpDrawer.execStep5") }}</div>')

# Monitor
content = content.replace(
    '<h3 class="help-h3">Node Actions</h3>',
    '<h3 class="help-h3">{{ $t("message.helpDrawer.nodeActions") }}</h3>')
content = content.replace(
    '<div class="help-grid-item"><strong>Retry</strong> — Re-execute a failed node</div>',
    '<div class="help-grid-item">{{ $t("message.helpDrawer.actRetry") }}</div>')
content = content.replace(
    '<div class="help-grid-item"><strong>Skip</strong> — Skip a failed node</div>',
    '<div class="help-grid-item">{{ $t("message.helpDrawer.actSkip") }}</div>')
content = content.replace(
    '<div class="help-grid-item"><strong>Pause</strong> — Pause the pipeline</div>',
    '<div class="help-grid-item">{{ $t("message.helpDrawer.actPause") }}</div>')
content = content.replace(
    '<div class="help-grid-item"><strong>Cancel</strong> — Cancel execution</div>',
    '<div class="help-grid-item">{{ $t("message.helpDrawer.actCancel") }}</div>')

content = content.replace(
    '<h3 class="help-h3">Approval Nodes</h3>',
    '<h3 class="help-h3">{{ $t("message.helpDrawer.approvalNodes") }}</h3>')
content = content.replace(
    '<p>Pipelines with approval nodes pause there. Go to <strong>Approval Center</strong> to Approve/Reject — the pipeline auto-continues after approval.</p>',
    '<p>{{ $t("message.helpDrawer.approvalDesc") }}</p>')

content = content.replace(
    '<h3 class="help-h3">Logs</h3>',
    '<h3 class="help-h3">{{ $t("message.helpDrawer.logs") }}</h3>')
content = content.replace(
    '<p>Three tabs in the right panel: <strong>Logs</strong> (timeline), <strong>Traces</strong> (node trace table), <strong>Data</strong> (inputs/outputs)</p>',
    '<p>{{ $t("message.helpDrawer.logsDesc") }}</p>')

# Monitor desc
content = content.replace(
    '<p>Go to <strong>Execution Records</strong> → click an execution ID for detail:</p>',
    '<p>{{ $t("message.helpDrawer.monitorDesc") }}</p>')

# FAQ
faqs = [
    ('faq1q', 'Q: Why did my node fail?'),
    ('faq1a', 'Check: plugin selected? parameters complete? timeout reasonable? target host reachable?'),
    ('faq2q', "Q: How to reference another node's output?"),
    ('faq2a', 'Use ${node_id.output_key}, e.g. ${node_2.stdout} in parameters'),
    ('faq3q', 'Q: Draft vs Published difference?'),
    ('faq3a', 'Draft: editable but non-executable. Published: executable but requires a new version to edit'),
    ('faq4q', 'Q: Can I retry after execution failure?'),
    ('faq4a', 'Yes — select the failed node in the monitor canvas and click Retry or Skip'),
    ('faq5q', 'Q: How to write condition expressions?'),
]
for key, text in faqs:
    content = content.replace(text, '{{ $t("message.helpDrawer.' + key + '") }}')

# Handle Q5 answer (has code tags) and Q2 answer
content = content.replace(
    '<div class="help-faq-a">{{ $t("message.helpDrawer.faq2a") }}</div>',
    '<div class="help-faq-a" v-html="$t(\'message.helpDrawer.faq2a\', { code1: \'${node_id.output_key}\', code2: \'${node_2.stdout}\' })"></div>')
content = content.replace(
    '<div class="help-faq-a">{{ $t("message.helpDrawer.faq5a") }}</div>',
    '<div class="help-faq-a" v-html="$t(\'message.helpDrawer.faq5a\', { code1: \'${_result} == True\', code2: \'${node_2.cpu} > 80\' })"></div>')

if content != orig:
    with open(fp, 'w', encoding='utf-8') as f:
        f.write(content)
    print('HelpDrawer.vue: updated')
else:
    print('HelpDrawer.vue: no changes')

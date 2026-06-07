<template>
  <el-drawer
    v-model="visible"
    title="📖 Quick Start Guide"
    size="420px"
    direction="rtl"
    :close-on-click-modal="true"
    class="help-drawer"
  >
    <template #header>
      <div class="help-drawer-header">
        <div class="help-drawer-title">
          <span class="help-drawer-icon">📖</span>
          <span>Quick Start Guide</span>
        </div>
        <el-tag
          size="small"
          effect="plain"
          type="primary"
          style="cursor: pointer"
          @click="$emit('startTour')"
        >
          👉 5-Step Tour
        </el-tag>
      </div>
    </template>

    <div class="help-content" v-pre>
      <!-- Overview -->
      <section class="help-section">
        <h2 class="help-h2">Overview</h2>
        <div class="help-flow">
          <div class="help-flow-step">
            <span class="help-flow-num">①</span>
            <span>Create</span>
          </div>
          <div class="help-flow-arrow">→</div>
          <div class="help-flow-step">
            <span class="help-flow-num">②</span>
            <span>Design</span>
          </div>
          <div class="help-flow-arrow">→</div>
          <div class="help-flow-step">
            <span class="help-flow-num">③</span>
            <span>Publish</span>
          </div>
          <div class="help-flow-arrow">→</div>
          <div class="help-flow-step">
            <span class="help-flow-num">④</span>
            <span>Execute</span>
          </div>
          <div class="help-flow-arrow">→</div>
          <div class="help-flow-step">
            <span class="help-flow-num">⑤</span>
            <span>Monitor</span>
          </div>
        </div>
      </section>

      <!-- 1. Create Template -->
      <section class="help-section">
        <h2 class="help-h2">1. Create Template</h2>
        <div class="help-methods">
          <div class="help-method">
            <span class="help-method-icon">🤖</span>
            <div>
              <strong>AI Generate</strong>
              <p>Describe your workflow in natural language — AI builds the pipeline</p>
            </div>
          </div>
          <div class="help-method">
            <span class="help-method-icon">📄</span>
            <div>
              <strong>Blank Canvas</strong>
              <p>Drag nodes from the Stencil to build manually</p>
            </div>
          </div>
          <div class="help-method">
            <span class="help-method-icon">📋</span>
            <div>
              <strong>Clone Existing</strong>
              <p>Duplicate an existing template as a starting point</p>
            </div>
          </div>
        </div>
        <div class="help-tip">
          <strong>💡 Draft vs Published:</strong>
          New templates are drafts — editable but non-executable. Publish to create a version snapshot and enable execution.
        </div>
      </section>

      <!-- 2. Design Pipeline -->
      <section class="help-section">
        <h2 class="help-h2">2. Design Pipeline</h2>
        <div class="help-node-grid">
          <div class="help-node-item">
            <span class="help-node-tag help-node-tag-start">🟢</span>
            <span>Start / End</span>
          </div>
          <div class="help-node-item">
            <span class="help-node-tag help-node-tag-task">▢</span>
            <span>Task Node <em class="help-warn">plugin required</em></span>
          </div>
          <div class="help-node-item">
            <span class="help-node-tag help-node-tag-exclusive">🔷×</span>
            <span>Exclusive Gateway (condition)</span>
          </div>
          <div class="help-node-item">
            <span class="help-node-tag help-node-tag-parallel">🔷+</span>
            <span>Parallel Gateway (fan-out)</span>
          </div>
          <div class="help-node-item">
            <span class="help-node-tag help-node-tag-converge">🔷⊕</span>
            <span>Converge Gateway (join)</span>
          </div>
          <div class="help-node-item">
            <span class="help-node-tag help-node-tag-subprocess">⬜</span>
            <span>Subprocess (reuse template)</span>
          </div>
        </div>

        <h3 class="help-h3">Key Actions</h3>
        <ul class="help-list">
          <li>Drag nodes from the <strong>Stencil</strong> (left panel) onto the canvas</li>
          <li>Task nodes <strong>MUST select a plugin</strong> (Shell / Ansible / etc.) or they cannot execute</li>
          <li>Select a node → configure parameters, timeout, retry policy in the right Property Panel</li>
          <li>Variable reference: <code>${node_id.output_key}</code></li>
          <li>Edge condition: from Exclusive Gateway, set <code>${node_id.key} > 80</code></li>
        </ul>
      </section>

      <!-- 3. Publish Version -->
      <section class="help-section">
        <h2 class="help-h2">3. Publish Version</h2>
        <ol class="help-list">
          <li>Click <strong>Save</strong> in the toolbar to save the draft</li>
          <li>Click <strong>Publish</strong> (or the execution wizard triggers it automatically)</li>
          <li>Publishing freezes a snapshot — executions always read the snapshot, <strong>live edits are isolated</strong></li>
        </ol>
      </section>

      <!-- 4. Execution Flow -->
      <section class="help-section">
        <h2 class="help-h2">4. Execution Flow</h2>
        <p>Click <strong>▶ Execute</strong> to open the 5-step submission wizard:</p>
        <div class="help-wizard-steps">
          <div class="help-wiz-item">① AI Validation</div>
          <div class="help-wiz-item">② Link Change Request</div>
          <div class="help-wiz-item">③ Set Variables</div>
          <div class="help-wiz-item">④ Risk Assessment</div>
          <div class="help-wiz-item">⑤ Schedule</div>
        </div>
        <div class="help-states">
          <span class="help-state pending">pending</span>
          <span class="help-state-arrow">→</span>
          <span class="help-state running">running</span>
          <span class="help-state-arrow">→</span>
          <span class="help-state completed">completed ✓</span>
          <span class="help-state-divider">|</span>
          <span class="help-state failed">failed ✗ → Retry/Skip</span>
        </div>
      </section>

      <!-- 5. Monitor & Troubleshoot -->
      <section class="help-section">
        <h2 class="help-h2">5. Monitor & Troubleshoot</h2>
        <p>Go to <strong>Execution Records</strong> → click an execution ID for detail:</p>

        <h3 class="help-h3">Node Actions</h3>
        <div class="help-grid">
          <div class="help-grid-item"><strong>Retry</strong> — Re-execute a failed node</div>
          <div class="help-grid-item"><strong>Skip</strong> — Skip a failed node</div>
          <div class="help-grid-item"><strong>Pause</strong> — Pause the pipeline</div>
          <div class="help-grid-item"><strong>Cancel</strong> — Cancel execution</div>
        </div>

        <h3 class="help-h3">Approval Nodes</h3>
        <p>Pipelines with approval nodes pause there. Go to <strong>Approval Center</strong> to Approve/Reject — the pipeline auto-continues after approval.</p>

        <h3 class="help-h3">Logs</h3>
        <p>Three tabs in the right panel: <strong>Logs</strong> (timeline), <strong>Traces</strong> (node trace table), <strong>Data</strong> (inputs/outputs)</p>
      </section>

      <!-- 6. FAQ -->
      <section class="help-section">
        <h2 class="help-h2">6. FAQ</h2>

        <div class="help-faq">
          <div class="help-faq-q">Q: Why did my node fail?</div>
          <div class="help-faq-a">Check: plugin selected? parameters complete? timeout reasonable? target host reachable?</div>
        </div>

        <div class="help-faq">
          <div class="help-faq-q">Q: How to reference another node's output?</div>
          <div class="help-faq-a">Use <code>${node_id.output_key}</code>, e.g. <code>${node_2.stdout}</code> in parameters</div>
        </div>

        <div class="help-faq">
          <div class="help-faq-q">Q: Draft vs Published difference?</div>
          <div class="help-faq-a">Draft: editable but non-executable. Published: executable but requires a new version to edit</div>
        </div>

        <div class="help-faq">
          <div class="help-faq-q">Q: Can I retry after execution failure?</div>
          <div class="help-faq-a">Yes — select the failed node in the monitor canvas and click Retry or Skip</div>
        </div>

        <div class="help-faq">
          <div class="help-faq-q">Q: How to write condition expressions?</div>
          <div class="help-faq-a"><code>${_result} == True</code> or <code>${node_2.cpu} > 80</code></div>
        </div>
      </section>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = withDefaults(defineProps<{
  visible?: boolean
}>(), {
  visible: false,
})

const emit = defineEmits<{
  'startTour': []
  'update:visible': [v: boolean]
}>()

const visible = computed({
  get: () => props.visible,
  set: (v: boolean) => emit('update:visible', v),
})
</script>

<style lang="scss" scoped>
@use '../../styles/opsflow-global' as *;

.help-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 16px 20px;
  border-bottom: 1px solid $of-border-card;
}
.help-drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}
.help-drawer-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 700;
  color: $of-text-primary;
}
.help-drawer-icon {
  font-size: 20px;
}
.help-content {
  padding: 4px 20px 20px;
  font-size: 13px;
  line-height: 1.7;
  color: $of-text-secondary;
}
.help-section {
  margin-bottom: 22px;
}
.help-h2 {
  font-size: 15px;
  font-weight: 700;
  color: $of-text-primary;
  margin: 0 0 10px;
  padding-bottom: 6px;
  border-bottom: 2px solid $of-color-primary;
  display: inline-block;
}
.help-h3 {
  font-size: 13px;
  font-weight: 600;
  color: $of-text-muted;
  margin: 12px 0 6px;
}

/* Flow diagram */
.help-flow {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 12px 14px;
  background: $of-bg-card;
  border-radius: $of-radius-sm;
  border: 1px solid $of-border-default;
}
.help-flow-step {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  font-weight: 600;
  color: $of-text-secondary;
}
.help-flow-num {
  color: $of-color-primary;
}
.help-flow-arrow {
  color: $of-text-placeholder;
  font-size: 14px;
}

/* Creation methods */
.help-methods {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}
.help-method {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 8px 10px;
  background: #fff;
  border: 1px solid $of-border-default;
  border-radius: $of-radius-sm;
}
.help-method-icon {
  font-size: 18px;
  flex-shrink: 0;
  margin-top: 1px;
}
.help-method strong {
  display: block;
  font-size: 12px;
  margin-bottom: 1px;
}
.help-method p {
  margin: 0;
  font-size: 11px;
  color: $of-text-muted;
}
.help-tip {
  font-size: 12px;
  background: $of-bg-confirm;
  border: 1px solid $of-border-confirm;
  border-radius: 6px;
  padding: 8px 10px;
  color: #92400e;
}

/* Node grid */
.help-node-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
  margin-bottom: 8px;
}
.help-node-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  padding: 4px 6px;
  background: $of-bg-card-hover;
  border-radius: 4px;
}
.help-node-tag {
  flex-shrink: 0;
  width: 24px;
  height: 20px;
  border-radius: 3px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
}
.help-warn {
  color: #F56C6C;
  font-style: normal;
  font-size: 10px;
}
/* Node tag color variants — replaces inline styles */
.help-node-tag-start { background: #E1F3D8; color: #67C23A; }
.help-node-tag-task { background: #fff; color: $of-color-primary; border: 1px solid $of-color-primary; }
.help-node-tag-exclusive { background: #fff; color: #E6A23C; border: 1px solid #E6A23C; }
.help-node-tag-parallel { background: #fff; color: $of-color-primary; border: 1px solid $of-color-primary; }
.help-node-tag-converge { background: #fff; color: $of-text-muted; border: 1px solid $of-text-muted; }
.help-node-tag-subprocess { background: #EBF5FB; color: #2980B9; border: 1px dashed #2980B9; }

/* Lists */
.help-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 2;
  color: $of-text-muted;
}
.help-list code {
  background: $of-bg-light-blue;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 11px;
  color: $of-color-primary;
}

/* Wizard steps */
.help-wizard-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin: 8px 0;
}
.help-wiz-item {
  padding: 4px 10px;
  background: $of-bg-light-blue;
  border-radius: 12px;
  font-size: 11px;
  color: $of-color-primary;
  font-weight: 500;
}

/* State flow */
.help-states {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px 10px;
  background: $of-bg-card-hover;
  border-radius: 6px;
  font-size: 11px;
  font-family: monospace;
}
.help-state { padding: 2px 6px; border-radius: 3px; }
.help-state.pending { background: #f3f4f6; color: $of-text-muted; }
.help-state.running { background: $of-bg-warning; color: #d97706; }
.help-state.completed { background: $of-bg-success; color: #059669; }
.help-state.failed { background: $of-bg-danger; color: #dc2626; }
.help-state-arrow { color: $of-text-placeholder; }
.help-state-divider { color: $of-border-default; }

/* Grid actions */
.help-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}
.help-grid-item {
  padding: 6px 8px;
  background: $of-bg-card-hover;
  border-radius: 4px;
  font-size: 11px;
  color: $of-text-muted;
  border: 1px solid $of-border-card;
}

/* FAQ */
.help-faq {
  margin-bottom: 10px;
  padding: 10px;
  background: #fff;
  border: 1px solid $of-border-default;
  border-radius: $of-radius-sm;
}
.help-faq-q {
  font-weight: 600;
  font-size: 12px;
  color: $of-text-primary;
  margin-bottom: 4px;
}
.help-faq-a {
  font-size: 12px;
  color: $of-text-muted;
  line-height: 1.5;
}
.help-faq-a code {
  background: $of-bg-light-blue;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
  color: $of-color-primary;
}
</style>

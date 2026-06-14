<template>
  <el-drawer
    v-model="visible"
    size="420px"
    direction="rtl"
    :close-on-click-modal="true"
    class="help-drawer"
  >
    <template #header>
      <div class="help-drawer-header">
        <div class="help-drawer-title">
          <span class="help-drawer-icon">📖</span>
          <span>{{ $t('message.helpDrawer.title') }}</span>
        </div>
        <el-tag
          size="small"
          effect="plain"
          type="primary"
          style="cursor: pointer"
          @click="$emit('startTour')"
        >
          👉 {{ $t('message.helpDrawer.tourBtn') }}
        </el-tag>
      </div>
    </template>

    <div class="help-content">
      <!-- Overview -->
      <section class="help-section">
        <h2 class="help-h2">{{ $t('message.helpDrawer.overview') }}</h2>
        <div class="help-flow">
          <span class="help-flow-text">{{ $t('message.helpDrawer.flowOverview') }}</span>
        </div>
      </section>

      <!-- 1. Create Template -->
      <section class="help-section">
        <h2 class="help-h2">{{ $t('message.helpDrawer.createTemplate') }}</h2>
        <div class="help-methods">
          <div class="help-method">
            <span class="help-method-icon">🤖</span>
            <div>
              <strong>{{ $t('message.helpDrawer.aiGenerate') }}</strong>
              <p>{{ $t('message.helpDrawer.aiGenerateDesc') }}</p>
            </div>
          </div>
          <div class="help-method">
            <span class="help-method-icon">📄</span>
            <div>
              <strong>{{ $t('message.helpDrawer.blankCanvas') }}</strong>
              <p>{{ $t('message.helpDrawer.blankCanvasDesc') }}</p>
            </div>
          </div>
          <div class="help-method">
            <span class="help-method-icon">📋</span>
            <div>
              <strong>{{ $t('message.helpDrawer.cloneExisting') }}</strong>
              <p>{{ $t('message.helpDrawer.cloneExistingDesc') }}</p>
            </div>
          </div>
        </div>
        <div class="help-tip">
          <strong>{{ $t('message.helpDrawer.draftTip') }}</strong>
          {{ $t('message.helpDrawer.draftTipDesc') }}
        </div>
      </section>

      <!-- 2. Design Pipeline -->
      <section class="help-section">
        <h2 class="help-h2">{{ $t('message.helpDrawer.designPipeline') }}</h2>
        <div class="help-node-grid">
          <div class="help-node-item">
            <span class="help-node-tag help-node-tag-start">🟢</span>
            <span>{{ $t('message.helpDrawer.startEnd') }}</span>
          </div>
          <div class="help-node-item">
            <span class="help-node-tag help-node-tag-task">▢</span>
            <span>{{ $t('message.helpDrawer.taskNode') }} <em class="help-warn">{{ $t('message.helpDrawer.pluginRequired') }}</em></span>
          </div>
          <div class="help-node-item">
            <span class="help-node-tag help-node-tag-exclusive">🔷×</span>
            <span>{{ $t('message.helpDrawer.exclusiveGateway') }}</span>
          </div>
          <div class="help-node-item">
            <span class="help-node-tag help-node-tag-parallel">🔷+</span>
            <span>{{ $t('message.helpDrawer.parallelGateway') }}</span>
          </div>
          <div class="help-node-item">
            <span class="help-node-tag help-node-tag-converge">🔷⊕</span>
            <span>{{ $t('message.helpDrawer.convergeGateway') }}</span>
          </div>
          <div class="help-node-item">
            <span class="help-node-tag help-node-tag-subprocess">⬜</span>
            <span>{{ $t('message.helpDrawer.subprocess') }}</span>
          </div>
        </div>

        <h3 class="help-h3">{{ $t('message.helpDrawer.keyActions') }}</h3>
        <ul class="help-list">
          <li>{{ $t('message.helpDrawer.actionDrag') }}</li>
          <li>{{ $t('message.helpDrawer.actionPlugin') }}</li>
          <li>{{ $t('message.helpDrawer.actionConfig') }}</li>
          <li v-html="$t('message.helpDrawer.actionVar', { code: '<code>${node_id.output_key}</code>' })" />
          <li v-html="$t('message.helpDrawer.actionEdge', { code: '<code>${node_id.key} &gt; 80</code>' })" />
        </ul>
      </section>

      <!-- 3. Publish Version -->
      <section class="help-section">
        <h2 class="help-h2">{{ $t('message.helpDrawer.publishVersion') }}</h2>
        <ol class="help-list">
          <li v-html="$t('message.helpDrawer.pubSave')" />
          <li v-html="$t('message.helpDrawer.pubPublish')" />
          <li v-html="$t('message.helpDrawer.pubSnapshot')" />
        </ol>
      </section>

      <!-- 4. Execution Flow -->
      <section class="help-section">
        <h2 class="help-h2">{{ $t('message.helpDrawer.executionFlow') }}</h2>
        <p v-html="$t('message.helpDrawer.execDesc')" />
        <div class="help-wizard-steps">
          <div class="help-wiz-item">① {{ $t('message.helpDrawer.execStep1') }}</div>
          <div class="help-wiz-item">② {{ $t('message.helpDrawer.execStep2') }}</div>
          <div class="help-wiz-item">③ {{ $t('message.helpDrawer.execStep3') }}</div>
          <div class="help-wiz-item">④ {{ $t('message.helpDrawer.execStep4') }}</div>
          <div class="help-wiz-item">⑤ {{ $t('message.helpDrawer.execStep5') }}</div>
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
        <h2 class="help-h2">{{ $t('message.helpDrawer.monitorTitle') }}</h2>
        <p v-html="$t('message.helpDrawer.monitorDesc')" />

        <h3 class="help-h3">{{ $t('message.helpDrawer.nodeActions') }}</h3>
        <div class="help-grid">
          <div class="help-grid-item"><strong>Retry</strong> — {{ $t('message.helpDrawer.actRetry') }}</div>
          <div class="help-grid-item"><strong>Skip</strong> — {{ $t('message.helpDrawer.actSkip') }}</div>
          <div class="help-grid-item"><strong>Pause</strong> — {{ $t('message.helpDrawer.actPause') }}</div>
          <div class="help-grid-item"><strong>Cancel</strong> — {{ $t('message.helpDrawer.actCancel') }}</div>
        </div>

        <h3 class="help-h3">{{ $t('message.helpDrawer.approvalNodes') }}</h3>
        <p v-html="$t('message.helpDrawer.approvalDesc')" />

        <h3 class="help-h3">{{ $t('message.helpDrawer.logs') }}</h3>
        <p v-html="$t('message.helpDrawer.logsDesc')" />
      </section>

      <!-- 6. FAQ -->
      <section class="help-section">
        <h2 class="help-h2">{{ $t('message.helpDrawer.faq') }}</h2>

        <div class="help-faq">
          <div class="help-faq-q">{{ $t('message.helpDrawer.faq1q') }}</div>
          <div class="help-faq-a">{{ $t('message.helpDrawer.faq1a') }}</div>
        </div>

        <div class="help-faq">
          <div class="help-faq-q">{{ $t('message.helpDrawer.faq2q') }}</div>
          <div class="help-faq-a" v-html="$t('message.helpDrawer.faq2a', { code1: '<code>${node_id.output_key}</code>', code2: '<code>${node_2.stdout}</code>' })" />
        </div>

        <div class="help-faq">
          <div class="help-faq-q">{{ $t('message.helpDrawer.faq3q') }}</div>
          <div class="help-faq-a">{{ $t('message.helpDrawer.faq3a') }}</div>
        </div>

        <div class="help-faq">
          <div class="help-faq-q">{{ $t('message.helpDrawer.faq4q') }}</div>
          <div class="help-faq-a">{{ $t('message.helpDrawer.faq4a') }}</div>
        </div>

        <div class="help-faq">
          <div class="help-faq-q">{{ $t('message.helpDrawer.faq5q') }}</div>
          <div class="help-faq-a" v-html="$t('message.helpDrawer.faq5a', { code1: '<code>${_result} == True</code>', code2: '<code>${node_2.cpu} &gt; 80</code>' })" />
        </div>
      </section>
    </div>
  </el-drawer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

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
@use '/@/styles/global' as *;

.help-drawer :deep(.el-drawer__header) {
  margin-bottom: 0;
  padding: 16px 20px;
  border-bottom: 1px solid $g-border-card;
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
  color: $g-text-primary;
}
.help-drawer-icon {
  font-size: 20px;
}
.help-content {
  padding: 4px 20px 20px;
  font-size: 13px;
  line-height: 1.7;
  color: $g-text-secondary;
}
.help-section {
  margin-bottom: 22px;
}
.help-h2 {
  font-size: 15px;
  font-weight: 700;
  color: $g-text-primary;
  margin: 0 0 10px;
  padding-bottom: 6px;
  border-bottom: 2px solid $g-color-primary;
  display: inline-block;
}
.help-h3 {
  font-size: 13px;
  font-weight: 600;
  color: $g-text-muted;
  margin: 12px 0 6px;
}

/* Flow diagram */
.help-flow {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 12px 14px;
  background: $g-bg-card;
  border-radius: $g-radius-sm;
  border: 1px solid $g-border-default;
}
.help-flow-text {
  font-size: 13px;
  font-weight: 600;
  color: $g-text-primary;
  letter-spacing: 0.5px;
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
  border: 1px solid $g-border-default;
  border-radius: $g-radius-sm;
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
  color: $g-text-muted;
}
.help-tip {
  font-size: 12px;
  background: $g-bg-confirm;
  border: 1px solid $g-border-confirm;
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
  background: $g-bg-card-hover;
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
.help-node-tag-task { background: #fff; color: $g-color-primary; border: 1px solid $g-color-primary; }
.help-node-tag-exclusive { background: #fff; color: #E6A23C; border: 1px solid #E6A23C; }
.help-node-tag-parallel { background: #fff; color: $g-color-primary; border: 1px solid $g-color-primary; }
.help-node-tag-converge { background: #fff; color: $g-text-muted; border: 1px solid $g-text-muted; }
.help-node-tag-subprocess { background: #EBF5FB; color: #2980B9; border: 1px dashed #2980B9; }

/* Lists */
.help-list {
  margin: 0;
  padding-left: 18px;
  font-size: 12px;
  line-height: 2;
  color: $g-text-muted;
}
.help-list :deep(code) {
  background: $g-bg-light-blue;
  padding: 1px 5px;
  border-radius: 3px;
  font-size: 11px;
  color: $g-color-primary;
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
  background: $g-bg-light-blue;
  border-radius: 12px;
  font-size: 11px;
  color: $g-color-primary;
  font-weight: 500;
}

/* State flow */
.help-states {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px 10px;
  background: $g-bg-card-hover;
  border-radius: 6px;
  font-size: 11px;
  font-family: monospace;
}
.help-state { padding: 2px 6px; border-radius: 3px; }
.help-state.pending { background: #f3f4f6; color: $g-text-muted; }
.help-state.running { background: $g-bg-warning; color: #d97706; }
.help-state.completed { background: $g-bg-success; color: #059669; }
.help-state.failed { background: $g-bg-danger; color: #dc2626; }
.help-state-arrow { color: $g-text-placeholder; }
.help-state-divider { color: $g-border-default; }

/* Grid actions */
.help-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px;
}
.help-grid-item {
  padding: 6px 8px;
  background: $g-bg-card-hover;
  border-radius: 4px;
  font-size: 11px;
  color: $g-text-muted;
  border: 1px solid $g-border-card;
}

/* FAQ */
.help-faq {
  margin-bottom: 10px;
  padding: 10px;
  background: #fff;
  border: 1px solid $g-border-default;
  border-radius: $g-radius-sm;
}
.help-faq-q {
  font-weight: 600;
  font-size: 12px;
  color: $g-text-primary;
  margin-bottom: 4px;
}
.help-faq-a {
  font-size: 12px;
  color: $g-text-muted;
  line-height: 1.5;
}
.help-faq-a :deep(code) {
  background: $g-bg-light-blue;
  padding: 1px 4px;
  border-radius: 3px;
  font-size: 11px;
  color: $g-color-primary;
}
</style>

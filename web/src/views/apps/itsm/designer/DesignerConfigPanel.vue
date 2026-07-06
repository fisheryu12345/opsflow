<template>
  <div class="des-config" v-if="configVisible">
    <div class="des-config-header">
      <span>{{ configTitle }}</span>
      <el-button text size="small" @click="$emit('close')">
        <el-icon><Close /></el-icon>
      </el-button>
    </div>
    <div class="des-config-body">
      <!-- Node config -->
      <template v-if="node">
        <el-form label-position="top" size="small">
          <el-form-item :label="$t('message.designer.nodeName')">
            <el-input v-model="node.name" @input="onChange" />
          </el-form-item>
          <el-form-item :label="$t('message.designer.nodeId')">
            <el-input :model-value="node.node_key || node._x6Id" disabled />
          </el-form-item>
          <el-form-item :label="$t('message.designer.nodeType')">
            <el-tag size="small">{{ typeLabel }}</el-tag>
          </el-form-item>

          <!-- APPROVAL -->
          <template v-if="node.type === 'APPROVAL'">
            <el-form-item :label="$t('message.designer.processorType')">
              <el-select v-model="node.processors_type" @change="onChange" style="width:100%">
                <el-option :label="$t('message.designer.starterLeader')" value="STARTER_LEADER" />
                <el-option :label="$t('message.designer.designatedPerson')" value="PERSON" />
                <el-option :label="$t('message.designer.role')" value="ROLE" />
                <el-option :label="$t('message.designer.starter')" value="STARTER" />
              </el-select>
            </el-form-item>
            <template v-if="node.processors_type === 'PERSON'">
              <el-form-item :label="$t('message.designer.processor')">
                <el-select v-model="personUsers" multiple filterable size="small" style="width:100%"
                  :loading="usersLoading" :placeholder="$t('message.designer.searchUserPlaceholder')" @focus="loadUsers" @change="onPersonChange">
                  <el-option v-for="u in userOptions" :key="u.username" :label="`${u.name} (${u.username})`" :value="u.username" />
                </el-select>
              </el-form-item>
            </template>
            <el-form-item v-if="node.processors_type === 'ROLE'" :label="$t('message.designer.processor')">
              <el-input v-model="node.processorsRaw" @input="onChange" :placeholder="$t('message.designer.rolePlaceholder')" />
            </el-form-item>
            <el-form-item :label="$t('message.designer.approvalMethod')">
              <el-radio-group v-model="node.is_multi" @change="onChange">
                <el-radio :label="false">{{ $t('message.designer.singleSign') }}</el-radio>
                <el-radio :label="true">{{ $t('message.designer.multiSign') }}</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item :label="$t('message.designer.allowSkip')">
              <el-switch v-model="node.is_allow_skip" @change="onChange" />
            </el-form-item>
          </template>

          <!-- SIGN -->
          <template v-if="node.type === 'SIGN'">
            <el-form-item :label="$t('message.designer.processorType')">
              <el-select v-model="node.processors_type" @change="onChange" style="width:100%">
                <el-option :label="$t('message.designer.starterLeader')" value="STARTER_LEADER" />
                <el-option :label="$t('message.designer.designatedPerson')" value="PERSON" />
                <el-option :label="$t('message.designer.role')" value="ROLE" />
                <el-option :label="$t('message.designer.starter')" value="STARTER" />
              </el-select>
            </el-form-item>
            <template v-if="node.processors_type === 'PERSON'">
              <el-form-item :label="$t('message.designer.processor')">
                <el-select v-model="personUsers" multiple filterable size="small" style="width:100%"
                  :loading="usersLoading" :placeholder="$t('message.designer.searchUserPlaceholder')" @focus="loadUsers" @change="onPersonChange">
                  <el-option v-for="u in userOptions" :key="u.username" :label="`${u.name} (${u.username})`" :value="u.username" />
                </el-select>
              </el-form-item>
            </template>
            <el-form-item v-if="node.processors_type === 'ROLE'" :label="$t('message.designer.processor')">
              <el-input v-model="node.processorsRaw" @input="onChange" :placeholder="$t('message.designer.rolePlaceholder')" />
            </el-form-item>
            <el-form-item :label="$t('message.designer.signMethod')">
              <el-radio-group v-model="node.is_sequential" @change="onChange">
                <el-radio :label="false">{{ $t('message.designer.parallelSign') }}</el-radio>
                <el-radio :label="true">{{ $t('message.designer.sequentialSign') }}</el-radio>
              </el-radio-group>
            </el-form-item>
          </template>

          <!-- NORMAL (填单) — 提单人自己填写，不需要处理人配置 -->
          <template v-if="node.type === 'NORMAL'">
          </template>

          <!-- TASK -- with WEBHOOK -->
          <template v-if="node.type === 'TASK'">
            <el-form-item :label="$t('message.designer.processorType')">
              <el-select v-model="node.processors_type" @change="onChange" style="width:100%">
                <el-option :label="$t('message.designer.starter')" value="STARTER" />
                <el-option :label="$t('message.designer.designatedPerson')" value="PERSON" />
                <el-option :label="$t('message.designer.role')" value="ROLE" />
              </el-select>
            </el-form-item>
            <template v-if="node.processors_type === 'PERSON'">
              <el-form-item :label="$t('message.designer.processor')">
                <el-select v-model="personUsers" multiple filterable size="small" style="width:100%"
                  :loading="usersLoading" :placeholder="$t('message.designer.searchUserPlaceholder')" @focus="loadUsers" @change="onPersonChange">
                  <el-option v-for="u in userOptions" :key="u.username" :label="`${u.name} (${u.username})`" :value="u.username" />
                </el-select>
              </el-form-item>
            </template>
            <el-form-item v-if="node.processors_type === 'ROLE'" :label="$t('message.designer.processor')">
              <el-input v-model="node.processorsRaw" @input="onChange" :placeholder="$t('message.designer.rolePlaceholder')" />
            </el-form-item>
            <!-- TASK only: execute type -->
            <template v-if="node.type === 'TASK'">
              <el-form-item :label="$t('message.designer.executeType')">
                <el-radio-group v-model="node.execute_type" @change="onChange">
                  <el-radio label="internal">{{ $t('message.designer.internalExec') }}</el-radio>
                  <el-radio label="webhook">{{ $t('message.designer.webhookExec') }}</el-radio>
                </el-radio-group>
              </el-form-item>
              <template v-if="node.execute_type === 'webhook'">
                <el-form-item :label="$t('message.designer.requestUrl')">
                  <el-input v-model="node.api_url" @input="onChange" placeholder="https://..." />
                </el-form-item>
                <el-form-item :label="$t('message.designer.requestMethod')">
                  <el-select v-model="node.api_method" @change="onChange" style="width:100%">
                    <el-option label="POST" value="POST" />
                    <el-option label="GET" value="GET" />
                    <el-option label="PUT" value="PUT" />
                  </el-select>
                </el-form-item>
              </template>
            </template>
          </template>

          <!-- Fields button (all except gateways) -->
          <template v-if="!['COVERAGE', 'EXCLUSIVE', 'CONDITIONAL_PARALLEL', 'PARALLEL'].includes(node.type)">
            <el-form-item :label="$t('message.designer.formDesign')">
              <template v-if="node.type === 'NORMAL'">
                <div style="display:flex;align-items:center;gap:6px;width:100%">
                  <el-button size="small" type="primary" plain @click="onOpenFieldEditor">
                    <el-icon><Plus /></el-icon> {{ $t('message.designer.addField') }}
                  </el-button>
                  <span v-if="(node.fields || []).length" style="font-size:12px;color:#909399">
                    {{ $t('message.designer.configStatus', { n: (node.fields || []).length }) }}
                  </span>
                </div>
                <div v-if="!(node.fields || []).length" style="font-size:12px;color:#C0C4CC;margin-top:2px">
                  {{ $t('message.designer.emptyTip') }}
                </div>
              </template>
              <template v-else>
                <div style="display:flex;flex-wrap:wrap;gap:4px;margin-bottom:6px">
                  <el-tag
                    v-for="f in (node.fields || []).slice(0, 6)"
                    :key="f.key"
                    size="small"
                    :type="f.required ? 'danger' : 'info'"
                  >{{ f.name }}</el-tag>
                  <el-tag v-if="(node.fields || []).length > 6" size="small">
                    +{{ (node.fields || []).length - 6 }}
                  </el-tag>
                </div>
                <el-button size="small" @click="onOpenFieldEditor">
                  <el-icon><Edit /></el-icon> {{ $t('message.designer.editField') }}
                </el-button>
              </template>
            </el-form-item>
          </template>

          <!-- Gateway hint -->
          <template v-if="['COVERAGE', 'EXCLUSIVE', 'CONDITIONAL_PARALLEL', 'PARALLEL'].includes(node.type)">
            <el-alert type="info" :closable="false" show-icon :title="gatewayHint(node.type)" />
          </template>
        </el-form>
      </template>

      <!-- Edge config -->
      <template v-else-if="edge">
        <el-form label-position="top" size="small">
          <el-form-item :label="$t('message.designer.edgeLabel')">
            <el-input v-model="edge.label" :placeholder="$t('message.designer.edgeLabel')" @input="onEdgeChange" />
          </el-form-item>
          <el-form-item :label="$t('message.designer.conditionExpr')">
            <el-input v-model="edge.condition" type="textarea" :rows="2" :placeholder="$t('message.designer.conditionExprPlaceholder')" @input="onEdgeChange" />
          </el-form-item>
          <el-form-item :label="$t('message.designer.rejectEdge')">
            <el-switch v-model="edge.isReject" @change="onEdgeChange" />
            <span style="font-size:11px;color:#909399;margin-left:8px;">{{ $t('message.designer.rejectTip') }}</span>
          </el-form-item>
        </el-form>
      </template>
    </div>
    <button class="des-config-collapse" @click="$emit('close')">◀</button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Close, Edit, Plus } from '@element-plus/icons-vue'
import { getNodeConfig } from './shapes'
import { request } from '/@/utils/service'

const { t } = useI18n()

const props = defineProps<{
  node: any
  edge: any
}>()

const emit = defineEmits<{
  close: []
  change: []
  openFieldEditor: []
}>()

const configVisible = computed(() => props.node || props.edge)
const configTitle = computed(() => props.node ? t('message.designer.nodeConfig') : t('message.designer.edgeConfig'))
const typeLabel = computed(() => {
  if (!props.node?.type) return ''
  return getNodeConfig(props.node.type).label
})

function onChange() { emit('change') }
function onEdgeChange() { emit('change') }
function onOpenFieldEditor() { emit('openFieldEditor') }
function gatewayHint(type: string) {
  const hints: Record<string, string> = {
    COVERAGE: '汇聚网关 — 等待所有并行分支完成后继续',
    EXCLUSIVE: '排他网关 — 首个匹配条件的分支执行，其他跳过；需至少有一条无条件边',
    CONDITIONAL_PARALLEL: '条件并行网关 — 所有匹配条件的分支同时执行，需配合汇聚网关使用',
    PARALLEL: '并行网关 — 所有分支同时执行，需配合汇聚网关使用',
  }
  return hints[type] || ''
}

// 当节点 processors_type 变为 PERSON 时，从 node.processorsRaw 同步 personUsers
watch(() => props.node?.processors_type, (val) => {
  if (val === 'PERSON' && props.node?.processorsRaw) {
    personUsers.value = props.node.processorsRaw.split(',').filter(Boolean)
  } else if (val !== 'PERSON') {
    personUsers.value = []
  }
})

// ===== PERSON 处理人用户选择 =====
const personUsers = ref<string[]>([])
const usersLoading = ref(false)
const userOptions = ref<any[]>([])

async function loadUsers() {
  if (userOptions.value.length) return
  usersLoading.value = true
  try {
    const res: any = await request({ url: '/api/iam/users/search/', method: 'get', params: { page_size: 10000 } })
    userOptions.value = ((res as any).data || []).map((item: any) => ({ id: item.value, name: item.label }))
  } catch { userOptions.value = [] }
  usersLoading.value = false
}

function onPersonChange() {
  if (props.node) props.node.processorsRaw = (personUsers.value || []).join(',')
  onChange()
}
</script>

<style scoped>
.des-config {
  width: 320px; border-left: 1px solid #e4e7ed;
  background: #fff; overflow-y: auto; flex-shrink: 0;
  display: flex; flex-direction: column;
  position: relative;
}
.des-config-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 8px 12px; background: #f5f7fa; border-bottom: 1px solid #e4e7ed;
  font-size: 13px; font-weight: 600; color: #303133; flex-shrink: 0;
}
.des-config-body { flex: 1; padding: 12px; overflow-y: auto; }
.des-config-collapse {
  position: absolute; left: -16px; top: 50%; transform: translateY(-50%);
  width: 16px; height: 48px; border: 1px solid #e4e7ed; border-right: none;
  background: #f5f7fa; cursor: pointer; border-radius: 4px 0 0 4px;
  color: #909399; font-size: 10px; display: flex; align-items: center;
  justify-content: center;
}
.des-config-collapse:hover { color: #409EFF; background: #e8f0fe; }
</style>

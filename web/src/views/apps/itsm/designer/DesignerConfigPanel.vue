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
          <el-form-item label="节点名称">
            <el-input v-model="node.name" @input="onChange" />
          </el-form-item>
          <el-form-item label="节点类型">
            <el-tag size="small">{{ typeLabel }}</el-tag>
          </el-form-item>

          <!-- APPROVAL -->
          <template v-if="node.type === 'APPROVAL'">
            <el-form-item label="处理人类型">
              <el-select v-model="node.processors_type" @change="onChange" style="width:100%">
                <el-option label="提单人上级" value="STARTER_LEADER" />
                <el-option label="指定人员" value="PERSON" />
                <el-option label="角色" value="ROLE" />
                <el-option label="提单人" value="STARTER" />
              </el-select>
            </el-form-item>
            <template v-if="node.processors_type === 'PERSON'">
              <el-form-item label="处理人">
                <el-select v-model="personUsers" multiple filterable size="small" style="width:100%"
                  :loading="usersLoading" placeholder="搜索选择用户" @focus="loadUsers" @change="onPersonChange">
                  <el-option v-for="u in userOptions" :key="u.username" :label="`${u.name} (${u.username})`" :value="u.username" />
                </el-select>
              </el-form-item>
            </template>
            <el-form-item v-if="node.processors_type === 'ROLE'" label="处理人">
              <el-input v-model="node.processorsRaw" @input="onChange" placeholder="角色名称" />
            </el-form-item>
            <el-form-item label="审批方式">
              <el-radio-group v-model="node.is_multi" @change="onChange">
                <el-radio :label="false">单签（一人通过即可）</el-radio>
                <el-radio :label="true">会签（全部通过才过）</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="允许跳过">
              <el-switch v-model="node.is_allow_skip" @change="onChange" />
            </el-form-item>
          </template>

          <!-- SIGN -->
          <template v-if="node.type === 'SIGN'">
            <el-form-item label="处理人类型">
              <el-select v-model="node.processors_type" @change="onChange" style="width:100%">
                <el-option label="提单人上级" value="STARTER_LEADER" />
                <el-option label="指定人员" value="PERSON" />
                <el-option label="角色" value="ROLE" />
                <el-option label="提单人" value="STARTER" />
              </el-select>
            </el-form-item>
            <template v-if="node.processors_type === 'PERSON'">
              <el-form-item label="处理人">
                <el-select v-model="personUsers" multiple filterable size="small" style="width:100%"
                  :loading="usersLoading" placeholder="搜索选择用户" @focus="loadUsers" @change="onPersonChange">
                  <el-option v-for="u in userOptions" :key="u.username" :label="`${u.name} (${u.username})`" :value="u.username" />
                </el-select>
              </el-form-item>
            </template>
            <el-form-item v-if="node.processors_type === 'ROLE'" label="处理人">
              <el-input v-model="node.processorsRaw" @input="onChange" placeholder="角色名称" />
            </el-form-item>
            <el-form-item label="会签方式">
              <el-radio-group v-model="node.is_sequential" @change="onChange">
                <el-radio :label="false">并行会签（同时审批）</el-radio>
                <el-radio :label="true">顺序会签（逐一审批）</el-radio>
              </el-radio-group>
            </el-form-item>
          </template>

          <!-- NORMAL (填单) — 提单人自己填写，不需要处理人配置 -->
          <template v-if="node.type === 'NORMAL'">
          </template>

          <!-- TASK -- with WEBHOOK -->
          <template v-if="node.type === 'TASK'">
            <el-form-item label="处理人类型">
              <el-select v-model="node.processors_type" @change="onChange" style="width:100%">
                <el-option label="提单人" value="STARTER" />
                <el-option label="指定人员" value="PERSON" />
                <el-option label="角色" value="ROLE" />
              </el-select>
            </el-form-item>
            <template v-if="node.processors_type === 'PERSON'">
              <el-form-item label="处理人">
                <el-select v-model="personUsers" multiple filterable size="small" style="width:100%"
                  :loading="usersLoading" placeholder="搜索选择用户" @focus="loadUsers" @change="onPersonChange">
                  <el-option v-for="u in userOptions" :key="u.username" :label="`${u.name} (${u.username})`" :value="u.username" />
                </el-select>
              </el-form-item>
            </template>
            <el-form-item v-if="node.processors_type === 'ROLE'" label="处理人">
              <el-input v-model="node.processorsRaw" @input="onChange" placeholder="角色名称" />
            </el-form-item>
            <!-- TASK only: execute type -->
            <template v-if="node.type === 'TASK'">
              <el-form-item label="执行方式">
                <el-radio-group v-model="node.execute_type" @change="onChange">
                  <el-radio label="internal">内部执行</el-radio>
                  <el-radio label="webhook">外部调用</el-radio>
                </el-radio-group>
              </el-form-item>
              <template v-if="node.execute_type === 'webhook'">
                <el-form-item label="请求 URL">
                  <el-input v-model="node.api_url" @input="onChange" placeholder="https://..." />
                </el-form-item>
                <el-form-item label="请求方法">
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
          <template v-if="!['ROUTER_P', 'COVERAGE', 'EXCLUSIVE', 'CONDITIONAL'].includes(node.type)">
            <el-form-item label="工单设计">
              <template v-if="node.type === 'NORMAL'">
                <div style="display:flex;align-items:center;gap:6px;width:100%">
                  <el-button size="small" type="primary" plain @click="onOpenFieldEditor">
                    <el-icon><Plus /></el-icon> 添加字段
                  </el-button>
                  <span v-if="(node.fields || []).length" style="font-size:12px;color:#909399">
                    已配置 {{ (node.fields || []).length }} 项
                  </span>
                </div>
                <div v-if="!(node.fields || []).length" style="font-size:12px;color:#C0C4CC;margin-top:2px">
                  由申请人填写，需手动设计工单
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
                  <el-icon><Edit /></el-icon> 编辑字段
                </el-button>
              </template>
            </el-form-item>
          </template>

          <!-- Gateway hint -->
          <template v-if="['ROUTER_P', 'COVERAGE', 'EXCLUSIVE', 'CONDITIONAL'].includes(node.type)">
            <el-alert type="info" :closable="false" show-icon :title="node.type === 'ROUTER_P' ? '并行网关 — 所有分支同时执行，需配合汇聚网关使用' : '汇聚网关 — 等待所有并行分支完成后继续'" />
          </template>
        </el-form>
      </template>

      <!-- Edge config -->
      <template v-else-if="edge">
        <el-form label-position="top" size="small">
          <el-form-item label="标签">
            <el-input v-model="edge.label" placeholder="连线标签" @input="onEdgeChange" />
          </el-form-item>
          <el-form-item label="条件表达式">
            <el-input v-model="edge.condition" type="textarea" :rows="2" placeholder="如 ${node_1.field} == 'approved'" @input="onEdgeChange" />
          </el-form-item>
          <el-form-item label="驳回连线">
            <el-switch v-model="edge.isReject" @change="onEdgeChange" />
            <span style="font-size:11px;color:#909399;margin-left:8px;">审批节点驳回路径</span>
          </el-form-item>
        </el-form>
      </template>
    </div>
    <button class="des-config-collapse" @click="$emit('close')">◀</button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { Close, Edit, Plus } from '@element-plus/icons-vue'
import { getNodeConfig } from './shapes'
import { request } from '/@/utils/service'

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
const configTitle = computed(() => props.node ? '节点配置' : '连线配置')
const typeLabel = computed(() => {
  if (!props.node?.type) return ''
  return getNodeConfig(props.node.type).label
})

function onChange() { emit('change') }
function onEdgeChange() { emit('change') }
function onOpenFieldEditor() { emit('openFieldEditor') }

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
    const res: any = await request({ url: '/api/system/user/', method: 'get', params: { page_size: 10000 } })
    userOptions.value = (res as any).data?.results || (res as any).data || []
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

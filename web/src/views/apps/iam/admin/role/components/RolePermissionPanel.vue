<template>
  <el-dialog v-model="visible" title="权限配置" width="800px" top="5vh" destroy-on-close append-to-body @closed="$emit('closed')">
    <template #header>
      <div style="display:flex;align-items:center;gap:12px">
        <span>权限配置</span>
        <el-tag type="primary" effect="dark" round size="small">{{ roleName }}</el-tag>
      </div>
    </template>

    <div class="rpp-body" v-loading="loading">
      <el-empty v-if="!loading && menuTree.length === 0" description="暂无菜单数据" :image-size="60" />

      <el-row v-else :gutter="16">
        <!-- Left: Menu Tree -->
        <el-col :span="8">
          <div class="rpp-tree-panel">
            <div class="rpp-panel-title">菜单</div>
            <el-tree
              ref="treeRef"
              :data="menuTree"
              :props="{ label: 'name', children: 'children' }"
              node-key="id"
              show-checkbox
              default-expand-all
              check-strictly
              :default-checked-keys="checkedMenuIds"
              @check="onMenuCheck"
              @node-click="selectMenu"
              highlight-current
            />
          </div>
        </el-col>

        <!-- Right: Button permissions for selected menu -->
        <el-col :span="16">
          <div class="rpp-btn-panel">
            <div class="rpp-panel-title">
              按钮权限
              <span v-if="selectedMenu" style="color:#409EFF;margin-left:8px">— {{ selectedMenu.name }}</span>
            </div>
            <el-checkbox-group v-model="checkedBtnIds" v-if="selectedMenu && selectedMenuButtons.length">
              <div class="rpp-btn-grid">
                <el-checkbox v-for="btn in selectedMenuButtons" :key="btn.id" :label="btn.id" :value="btn.id">
                  {{ btn.name }}
                </el-checkbox>
              </div>
            </el-checkbox-group>
            <el-empty v-else-if="selectedMenu" description="该菜单无按钮权限" :image-size="40" />
            <div v-else class="rpp-hint">请从左侧菜单树选择一个菜单</div>
          </div>
        </el-col>
      </el-row>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { request } from '/@/utils/service'

const props = defineProps<{ modelValue: boolean; roleId: number; roleName: string }>()
const emit = defineEmits(['update:modelValue', 'closed'])

const visible = ref(props.modelValue)
watch(() => props.modelValue, v => { visible.value = v; if (v) loadData() })
watch(visible, v => emit('update:modelValue', v))

const loading = ref(false)
const saving = ref(false)
const menuTree = ref<any[]>([])
const selectedMenu = ref<any>(null)
const selectedMenuButtons = ref<any[]>([])
const checkedMenuIds = ref<number[]>([])
const checkedBtnIds = ref<number[]>([])
const menuBtnMap = ref<Record<number, number[]>>({}) // menu_id -> checked btn ids

async function loadData() {
  loading.value = true
  try {
    // Load all menus
    const menuRes: any = await request({ url: '/api/iam/menu/', method: 'get' })
    const allMenus = (menuRes as any).results || (menuRes as any).data || []
    // Build tree
    const buildTree = (items: any[], parent: number | null = null): any[] =>
      items.filter((m: any) => m.parent === parent).map((m: any) => ({
        ...m, children: buildTree(items, m.id),
      }))
    menuTree.value = buildTree(allMenus, null)

    // Load role's current permissions
    const permRes: any = await request({
      url: '/api/iam/role_menu_button_permission/role_menu_get_button/',
      method: 'get',
      params: { role_id: props.roleId },
    })
    const perms = (permRes as any).results || (permRes as any).data || []
    // perms is [{menu_id, menu_button_id, ...}]
    checkedMenuIds.value = [...new Set(perms.map((p: any) => p.menu_id))]
    const mbMap: Record<number, number[]> = {}
    for (const p of perms) {
      if (!mbMap[p.menu_id]) mbMap[p.menu_id] = []
      if (p.menu_button_id) mbMap[p.menu_id].push(p.menu_button_id)
    }
    menuBtnMap.value = mbMap
  } catch { ElMessage.error('加载权限数据失败') }
  loading.value = false
}

function onMenuCheck(_node: any, data: { checkedKeys: number[] }) {
  checkedMenuIds.value = data.checkedKeys
}

function selectMenu(menu: any) {
  selectedMenu.value = menu
  loadMenuButtons(menu.id)
}

async function loadMenuButtons(menuId: number) {
  try {
    const res: any = await request({ url: '/api/iam/role_menu_button_permission/menu_to_button/', params: { menu: menuId } })
    selectedMenuButtons.value = (res as any).results || (res as any).data || []
    checkedBtnIds.value = menuBtnMap.value[menuId] || []
  } catch { selectedMenuButtons.value = [] }
}

async function handleSave() {
  saving.value = true
  try {
    // Build save payload
    const permissions = checkedMenuIds.value.map(mid => ({
      menu_id: mid,
      button_ids: menuBtnMap.value[mid] || [],
    }))
    await request({
      url: '/api/iam/role_menu_button_permission/set_role_premission/',
      method: 'post',
      data: { role_id: props.roleId, permissions },
    })
    ElMessage.success('权限保存成功')
    visible.value = false
  } catch { ElMessage.error('保存失败') }
  saving.value = false
}
</script>

<style lang="scss" scoped>
.rpp-body { min-height: 400px; }
.rpp-tree-panel, .rpp-btn-panel {
  border: 1px solid #e4e7ed; border-radius: 8px; padding: 12px; height: 100%; min-height: 380px;
}
.rpp-panel-title { font-size: 14px; font-weight: 600; color: #303133; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #ebeef5; }
.rpp-btn-grid { display: flex; flex-direction: column; gap: 8px; }
.rpp-hint { color: #C0C4CC; font-size: 13px; text-align: center; margin-top: 60px; }
</style>

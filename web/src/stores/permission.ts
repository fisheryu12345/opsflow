/**
 * IAM Permission Store — unified permission checking
 *
 * Combines platform-level permission codenames (from backend)
 * with project-level role checks.
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { useProjectStore } from './project'

export const usePermissionStore = defineStore('permission', () => {
  const perms = ref<string[]>([])
  const loaded = ref(false)
  const projectStore = useProjectStore()

  async function fetchPermissions() {
    try {
      const { request } = await import('/@/utils/service')
      const res = await request({ url: '/api/iam/my-full-permissions/', method: 'get' })
      perms.value = res.data || []
    } catch {
      perms.value = []
    }
    loaded.value = true
  }

  function hasPerm(codename: string): boolean {
    return perms.value.includes(codename)
  }

  const currentRole = computed(() => projectStore.currentProject?.role || null)
  const isAdmin = computed(() => currentRole.value === 'admin')
  const canEdit = computed(() => currentRole.value !== null && currentRole.value !== 'viewer')

  /**
   * Check if current user can perform an action.
   * @param action - 'view' | 'edit' | 'admin'
   */
  function can(action: 'view' | 'edit' | 'admin'): boolean {
    if (!currentRole.value) return false
    if (action === 'admin') return currentRole.value === 'admin'
    if (action === 'edit') return currentRole.value !== 'viewer'
    return true
  }

  function requestPerm(label: string, codename?: string) {
    window.dispatchEvent(new CustomEvent('iam:request-permission', {
      detail: { key: codename || 'opsflow:template:create', label },
    }))
  }

  return { perms, loaded, fetchPermissions, hasPerm, currentRole, isAdmin, canEdit, can, requestPerm }
})
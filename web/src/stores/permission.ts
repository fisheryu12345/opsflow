/**
 * IAM Permission Store — replaces dvadmin BtnPermissionStore
 *
 * Reads the current user's IAM role from stores/project.ts and exposes
 * simple computed helpers for permission checks.
 * No dvadmin MenuButton API calls needed.
 */
import { defineStore } from 'pinia'
import { computed } from 'vue'
import { useProjectStore } from './project'

export const usePermissionStore = defineStore('permission', () => {
  const projectStore = useProjectStore()

  const currentRole = computed(() => projectStore.currentProject?.role || 'viewer')
  const isAdmin = computed(() => currentRole.value === 'admin')
  const canEdit = computed(() => currentRole.value !== 'viewer')
  const isSuperuser = computed(() => currentRole.value === 'admin') // IAM admin = platform superuser for sub-products

  /**
   * Check if current user can perform an action.
   * @param action - 'view' | 'edit' | 'admin'
   */
  function can(action: 'view' | 'edit' | 'admin'): boolean {
    if (action === 'admin') return currentRole.value === 'admin'
    if (action === 'edit') return currentRole.value !== 'viewer'
    return true // viewer can always view
  }

  return { currentRole, isAdmin, canEdit, isSuperuser, can }
})

/**
 * IAM Permission Directive — unified permission gate with auto-request.
 *
 * Usage:
 *   <el-button v-can.edit>Edit</el-button>           <!-- must be editor+ -->
 *   <el-button v-can.admin>Delete</el-button>          <!-- must be admin -->
 *   <el-button v-can.admin="'itsm:workflow:delete'">   <!-- admin + auto-request key -->
 *
 * When user lacks permission:
 *  - Button is disabled with 🔒 prefix
 *  - Click opens global RequestPermission dialog with the key pre-filled
 *
 * Reads role from stores/permission.ts.
 */
import type { Directive, DirectiveBinding } from 'vue'
import { usePermissionStore } from '/@/stores/permission'

const vCan: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    const store = usePermissionStore()
    const permKey = typeof binding.value === 'string' && binding.value.includes(':') ? binding.value : null

    if (permKey) {
      if (store.hasPerm(permKey)) return
    }

    // No permission: disable + intercept click for auto-request
    el.setAttribute('disabled', 'true')
    el.classList.add('is-disabled', 'v-can-locked')

    // Add lock icon prefix to button text
    if (el.tagName === 'BUTTON') {
      const originalText = el.textContent || ''
      el.setAttribute('data-original-text', originalText)
      el.textContent = originalText ? `🔒 ${originalText}` : '🔒'
    }

    el.addEventListener('click', (e) => {
      e.preventDefault()
      e.stopPropagation()
      const label = el.getAttribute('data-original-text') || el.textContent?.replace('🔒 ', '') || 'Unknown'
      const key = permKey || `auto:${label.replace(/\s+/g, '_').toLowerCase()}`
      window.dispatchEvent(new CustomEvent('iam:request-permission', {
        detail: { key, label },
      }))
    }, true)
  },
}

export default vCan

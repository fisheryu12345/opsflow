/**
 * IAM Permission Directive — replaces v-auth / v-permission.
 *
 * Usage:
 *   <el-button v-can.edit>Edit</el-button>     <!-- editor or admin -->
 *   <el-button v-can.admin>Delete</el-button>   <!-- admin only -->
 *   <el-button v-can="'edit'">Edit</el-button> <!-- same as v-can.edit -->
 *
 * Reads role from stores/permission.ts (which reads stores/project.ts).
 */
import type { Directive, DirectiveBinding } from 'vue'
import { usePermissionStore } from '/@/stores/permission'

const vCan: Directive = {
  mounted(el: HTMLElement, binding: DirectiveBinding) {
    const store = usePermissionStore()
    const action = binding.arg || binding.value
    if (!store.can(action as 'view' | 'edit' | 'admin')) {
      el.remove()
    }
  },
}

export default vCan

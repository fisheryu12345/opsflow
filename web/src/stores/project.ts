/**
 * 全局 Project 上下文管理
 *
 * 所有子产品（opsflow、ITSM、cmdb 等）共享当前选中的 Project。
 * 切换项目时通过 window CustomEvent 'project-changed' 通知所有页面刷新。
 */
import { defineStore } from 'pinia'

const STORAGE_KEY = 'opsflow_active_project_id'

export interface MyProject {
  id: number
  name: string
  code?: string
  role: 'admin' | 'editor' | 'viewer'
  business_id?: number
  business_name?: string
}

export const useProjectStore = defineStore('project', {
  state: () => ({
    currentProjectId: null as number | null,
    myProjects: [] as MyProject[],
  }),

  getters: {
    currentProject: (state) =>
      state.myProjects.find((p) => p.id === state.currentProjectId) || null,
  },

  actions: {
    setCurrentProjectId(id: number | null) {
      this.currentProjectId = id
      if (id) {
        localStorage.setItem(STORAGE_KEY, String(id))
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }
      window.dispatchEvent(
        new CustomEvent('project-changed', { detail: { projectId: id } })
      )
    },

    async fetchMyProjects() {
      try {
        const { request } = await import('/@/utils/service')
        const res: any = await request({
          url: '/api/opsflow/projects/my_projects/',
          method: 'get',
        })
        this.myProjects = (res as any).results || (res as any).data || []

        // 恢复上次选中的项目
        const saved = localStorage.getItem(STORAGE_KEY)
        if (saved && this.myProjects.find((p) => p.id === Number(saved))) {
          this.currentProjectId = Number(saved)
        } else if (this.myProjects.length > 0 && !this.currentProjectId) {
          this.currentProjectId = this.myProjects[0].id
        } else if (this.myProjects.length === 0) {
          this.currentProjectId = null
        }
      } catch (e) {
        console.warn('[projectStore] Failed to fetch my projects:', e)
      }
    },
  },
})

import { defineStore } from 'pinia'
import { setProjectId } from '../api/request'
import type { FlowTemplate, FlowExecution, MyProject, OpsflowState } from '../types'

const STORAGE_KEY = 'opsflow_active_project_id'

export const useOpsflowStore = defineStore('opsflow', {
  state: (): OpsflowState => ({
    mode: 'design',
    currentTemplate: null,
    currentExecution: null,
    templates: [],
    executions: [],
    globalVariables: {},
    currentProjectId: null,
    projects: [],
    myProjects: [],
    showHelpDrawer: false,
  }),
  getters: {
    isDesignMode: (state) => state.mode === 'design',
    isMonitorMode: (state) => state.mode === 'monitor',
    currentProject: (state) => state.myProjects.find(p => p.id === state.currentProjectId) || null,
    isOnboarded: () => !!localStorage.getItem('opsflow_onboarded'),
    globalVariableList: (state) => {
      const vars = state.globalVariables
      return Object.entries(vars).map(([key, val]: [string, any]) => ({
        key,
        value: val?.value ?? '',
        type: val?.type ?? 'input',
        source_type: val?.source_type ?? 'manual',
        source_info: val?.source_info ?? null,
        description: val?.description ?? '',
        reference_count: val?.reference_count ?? 0,
        show_type: val?.show_type ?? true,
      }))
    },
  },
  actions: {
    setMode(mode: 'design' | 'monitor') {
      this.mode = mode
    },
    setCurrentTemplate(template: FlowTemplate | null) {
      this.currentTemplate = template
    },
    setCurrentExecution(execution: FlowExecution | null) {
      this.currentExecution = execution
    },
    setTemplates(list: FlowTemplate[]) {
      this.templates = list
    },
    setExecutions(list: FlowExecution[]) {
      this.executions = list
    },
    setGlobalVariables(vars: Record<string, any>) {
      this.globalVariables = vars
    },

    /** 设置当前项目 ID（同步更新 request.ts 和 localStorage） */
    setCurrentProjectId(id: number | null) {
      this.currentProjectId = id
      setProjectId(id)
      if (id) {
        localStorage.setItem(STORAGE_KEY, String(id))
      } else {
        localStorage.removeItem(STORAGE_KEY)
      }
    },

    setProjects(list: any[]) {
      this.projects = list
    },

    /** 加载当前用户可访问的项目列表（用于项目切换器） */
    async fetchMyProjects() {
      try {
        const { GetMyProjects } = await import('../api/projects')
        const res = await GetMyProjects()
        this.myProjects = res.data || []

        // 从 localStorage 恢复上次选中的项目
        const saved = localStorage.getItem(STORAGE_KEY)
        if (saved && this.myProjects.find(p => p.id === Number(saved))) {
          this.setCurrentProjectId(Number(saved))
        } else if (this.myProjects.length > 0 && !this.currentProjectId) {
          this.setCurrentProjectId(this.myProjects[0].id)
        } else if (this.myProjects.length === 0) {
          this.setCurrentProjectId(null)
        }
      } catch (e) {
        console.warn('Failed to fetch my projects:', e)
      }
    },

    async loadProjects() {
      try {
        const { GetProjects } = await import('../api/projects')
        const res = await GetProjects()
        this.projects = res.data || []
        if (!this.currentProjectId && this.projects.length > 0) {
          this.setCurrentProjectId(this.projects[0].id)
        }
      } catch (e) {
        console.warn('Failed to load projects:', e)
      }
    },

    toggleHelpDrawer() {
      this.showHelpDrawer = !this.showHelpDrawer
    },
    openHelpDrawer() {
      this.showHelpDrawer = true
    },
    closeHelpDrawer() {
      this.showHelpDrawer = false
    },


  },
})

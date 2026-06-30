import { defineStore } from 'pinia'
import { useProjectStore } from '/@/stores/project'
import { setProjectId } from '../api/request'
import type { FlowTemplate, FlowExecution, OpsflowState } from '../types'

export const useOpsflowStore = defineStore('opsflow', {
  state: (): OpsflowState => ({
    mode: 'design',
    currentTemplate: null,
    currentExecution: null,
    templates: [],
    executions: [],
    globalVariables: {},
    currentProjectId: null,   // proxy to stores/project.ts
    projects: [],
    myProjects: [],            // proxy to stores/project.ts
    showHelpDrawer: false,
  }),
  getters: {
    isDesignMode: (state) => state.mode === 'design',
    isMonitorMode: (state) => state.mode === 'monitor',
    currentProject: () => {
      const ps = useProjectStore()
      return ps.myProjects.find(p => p.id === ps.currentProjectId) || null
    },
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

    /** 设置当前项目 ID (委托给全局 projectStore) */
    setCurrentProjectId(id: number | null) {
      const ps = useProjectStore()
      this.currentProjectId = id
      ps.setCurrentProjectId(id)
      // Keep backward compat: sync setProjectId for opsflow request.ts
      setProjectId(id)
    },

    setProjects(list: any[]) {
      this.projects = list
    },

    /** 加载当前用户可访问的项目列表（委托给全局 projectStore） */
    async fetchMyProjects() {
      const ps = useProjectStore()
      await ps.fetchMyProjects()
      this.myProjects = ps.myProjects
      this.currentProjectId = ps.currentProjectId
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

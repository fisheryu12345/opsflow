import { defineStore } from 'pinia'

interface FlowTemplate {
  id: number
  name: string
  pipeline_tree: any
  target_hosts: string[]
  global_vars: any
  is_draft: boolean
  ai_original_tree: any
  created_by_name: string
  created_at: string
  updated_at: string
}

interface FlowExecution {
  id: number
  template: number
  template_name: string
  status: string
  node_status: Record<string, string>
  context: any
  current_node: string
  started_at: string | null
  ended_at: string | null
  created_by_name: string
  created_at: string
}

interface OpsflowState {
  mode: 'design' | 'monitor'
  currentTemplate: FlowTemplate | null
  currentExecution: FlowExecution | null
  templates: FlowTemplate[]
  executions: FlowExecution[]
  globalVariables: Record<string, any>
}

export const useOpsflowStore = defineStore('opsflow', {
  state: (): OpsflowState => ({
    mode: 'design',
    currentTemplate: null,
    currentExecution: null,
    templates: [],
    executions: [],
    globalVariables: {},
  }),
  getters: {
    isDesignMode: (state) => state.mode === 'design',
    isMonitorMode: (state) => state.mode === 'monitor',
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
  },
})

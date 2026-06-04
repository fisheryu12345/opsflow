/**
 * OpsFlow 共享类型定义
 * 所有跨组件使用的接口集中在此，减少分散定义
 */

// ── Template Domain ──
export interface FlowTemplate {
  id: number
  name: string
  pipeline_tree: any
  target_hosts: string[]
  global_vars: any
  is_draft: boolean
  is_public?: boolean
  project_scope?: string[]
  ai_original_tree: any
  created_by_name: string
  created_at: string
  updated_at: string
}

export interface TemplateVersion {
  version: number
  pipeline_tree: any
  target_hosts: string[]
  global_vars: any
  version_note: string
  created_at: string
}

// ── Execution Domain ──
export interface FlowExecution {
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

export interface NodeTrace {
  node_id: string
  node_label: string
  status: string
  retry_count: number
  duration_ms: number | null
  entered_at: string | null
  exited_at: string | null
  outputs: any
  error: string
}

// ── Project Domain ──
export interface MyProject {
  id: number
  name: string
  role: string
}

// ── Plugin Domain ──
export interface PluginInfo {
  code: string
  name: string
  group: string
  version: string
  description: string
  risk_level: string
  icon: string
  color: string
  phase: number
  is_active: boolean
  form_schema: any[]
  output_schema: any[]
}

// ── Pipeline / Graph Domain ──
export interface PipelineNode {
  id: string
  label: string
  node_type: string
  atom_type: string
  params: Record<string, any>
  x?: number
  y?: number
  max_retries?: number
  timeout_seconds?: number
  risk_level?: string
}

export interface PipelineEdge {
  from: string
  to: string
  label?: string
}

export interface PipelineTree {
  nodes: PipelineNode[]
  edges: PipelineEdge[]
}

export interface OutputField {
  source: string
  field: string
  fieldLabel: string
  fieldType: string
  sourceType: string
}

export interface VariableOption {
  source: string
  field: string
  fieldLabel: string
  fieldType: string
  sourceType: 'node' | 'global' | 'project' | 'system'
  value?: any
}

export interface ConditionRule {
  source: string
  field: string
  fieldLabel?: string
  fieldType?: string
  op: string
  value: string
}

export interface ConditionStruct {
  logic: 'AND' | 'OR'
  rules: ConditionRule[]
}

export interface OutputField {
  key: string
  label: string
  type: 'string' | 'number' | 'boolean'
  description?: string
}

export interface ValidationResult {
  valid: boolean
  errors: string[]
  warnings?: string[]
}

// ── Monitor Domain ──
export interface MonitorAttrs {
  fill: string
  stroke: string
  strokeWidth?: number
  strokeDash?: string
  label?: string
  labelStyle?: Record<string, any>
}

// ── Graph Canvas Options ──
export interface GraphCanvasOptions {
  container: HTMLElement
  readonly?: boolean
  width?: number
  height?: number
}

// ── Store Domain ──
export interface OpsflowState {
  mode: 'design' | 'monitor'
  currentTemplate: FlowTemplate | null
  currentExecution: FlowExecution | null
  templates: FlowTemplate[]
  executions: FlowExecution[]
  globalVariables: Record<string, any>
  currentProjectId: number | null
  projects: any[]
  myProjects: MyProject[]
  showHelpDrawer: boolean
}

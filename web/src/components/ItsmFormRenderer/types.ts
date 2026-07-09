/** ITSM workflow field definition (Schema B) */
export interface ItsmField {
  key: string
  name?: string
  type: ItsmFieldType
  required?: boolean
  layout?: ItsmLayout
  placeholder?: string
  default?: any
  choice?: { label: string; value: any }[]
  show_conditions?: { field: string; value: string }
  sort_order?: number
}

export type ItsmFieldType =
  | 'STRING'
  | 'TEXT'
  | 'INT'
  | 'DATE'
  | 'DATETIME'
  | 'SELECT'
  | 'RADIO'
  | 'CHECKBOX'
  | 'MULTISELECT'
  | 'MEMBERS'
  | 'FILE'
  | 'RICHTEXT'
  | 'TABLE'
  | 'CASCADE'
  | 'SECTION'
  | 'TREESELECT'

export type ItsmLayout = 'COL_12' | 'COL_8' | 'COL_6' | 'COL_4' | 'COL_3'

/** Map ITSM layout to flex-basis percentage */
export const LAYOUT_COL_MAP: Record<string, string> = {
  COL_12: '100%',
  COL_8: '66.66%',
  COL_6: '50%',
  COL_4: '33.33%',
  COL_3: '25%',
}

/** Renderer mode */
export type RendererMode = 'fill' | 'preview' | 'design'

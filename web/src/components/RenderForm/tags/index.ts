import { App } from 'vue'

/* ---------- Tag 组件注册 ---------- */
const modules = import.meta.glob('./Tag*.vue', { eager: true })

export function registerTags(app: App) {
  for (const path in modules) {
    const mod = modules[path] as any
    const name = path.replace('./Tag', '').replace('.vue', '')
    app.component(name, mod.default)
  }
}

export { default as TagInput } from './TagInput.vue'
export { default as TagSelect } from './TagSelect.vue'
export { default as TagTextarea } from './TagTextarea.vue'
export { default as TagCheckbox } from './TagCheckbox.vue'
export { default as TagRadio } from './TagRadio.vue'
export { default as TagInt } from './TagInt.vue'
export { default as TagCodeEditor } from './TagCodeEditor.vue'
export { default as TagDatetime } from './TagDatetime.vue'
export { default as TagHostSelector } from './TagHostSelector.vue'
export { default as TagAsyncSelect } from './TagAsyncSelect.vue'
export { default as TagIpSelector } from './TagIpSelector.vue'
export { default as TagDataTable } from './TagDataTable.vue'
export { default as TagVariableInput } from './TagVariableInput.vue'
export { default as TagMetaConfig } from './TagMetaConfig.vue'
export { default as TagVariableMapping } from './TagVariableMapping.vue'

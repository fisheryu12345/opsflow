import { computed, Ref } from 'vue'
import type { ItsmField } from './types'

/**
 * Composable for show_conditions visibility logic.
 * A field is visible iff its show_conditions.field equals show_conditions.value
 * in the current form data.
 */
export function useFieldVisibility(formData: Ref<Record<string, any>>) {
  function isVisible(field: ItsmField): boolean {
    const cond = field.show_conditions
    if (!cond?.field) return true
    const dependValue = formData.value[cond.field]
    return String(dependValue ?? '') === String(cond.value ?? '')
  }

  const visibleFields = computed(() => {
    // This is used at the renderer level — not all consumers need it,
    // but it's available for the parent component.
    return (fields: ItsmField[]) => fields.filter(f => isVisible(f))
  })

  return { isVisible, visibleFields }
}

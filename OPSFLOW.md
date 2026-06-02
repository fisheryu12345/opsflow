# OPSflow Style Guide

All OPSflow Vue components should follow these conventions for visual consistency.

**后续向导对话框参考:** `SubmitWizardDialog.vue` — 多步骤弹窗的 HTML/SCSS/动画标准实现。

### SCSS
- Use `<style lang="scss" scoped>` and `@import '../styles/opsflow-global';`
- Card containers: use `.of-card` class for standard card backgrounds/borders
- Dialogs: add class `opsflow-dialog` — header/body/footer styled automatically
- Animations: `.of-fade-in-up` for sections, `.of-stagger-item` for list items (keep inline `animation-delay`)
- Colors/gradients: use `$of-*` variables from `styles/opsflow-variables.scss`, never hardcode
- Hover effects: `@include of-hover-lift` (lift up) or `@include of-hover-shift` (shift right)

### HTML
- Class naming: kebab-case, component-prefixed (e.g. `mycomp-header`)
- Empty state: `<el-empty :image-size="40" />`

### Key Files
- `web/src/views/apps/opsflow/styles/opsflow-variables.scss` — design tokens
- `web/src/views/apps/opsflow/styles/opsflow-global.scss` — reusable classes & mixins

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

### 设计文档管理规则
所有通过 Superpowers 或其他 AI 工具生成的设计文档（架构设计、功能设计、详细设计等），**必须**遵守以下规则：

1. **保存路径**：统一保存到 `backend/opsflow/doc/design_plan/` 目录下
2. **文档格式**：必须同时生成 `.md`（Markdown）和 `.pdf` 两种格式
3. **文件命名**：`YYYY-MM-DD-<简短英文描述>.md`（如 `2026-06-03-gateway-condition-editor-design.md`）
4. **适用范围**：包括但不限于 Superpowers、SPARC 流程、Claude Code、以及其他 AI Agent 产出的设计文档

> 例外：本规则生效前已放置在 `opsflow/doc/` 根目录下的存量设计文档无需迁移。

# OPSflow Style Guide

## SCSS

```scss
// Import in every component:
<style lang="scss" scoped>
@import '../styles/opsflow-global';
```

### Design Tokens

All tokens defined in `web/src/views/apps/opsflow/styles/opsflow-variables.scss`:

| Category | Prefix | Examples |
|----------|--------|---------|
| Colors | `$of-color-*` | `primary` (#409EFF), `accent` (#667eea) |
| Backgrounds | `$of-bg-*` | `card` (#f8f9fb), `page` (#f0f2f5), `light-blue` (#ecf5ff) |
| Text | `$of-text-*` | `primary` (#303133), `secondary` (#666), `muted` (#909399) |
| Borders | `$of-border-*` | `default` (#e4e7ed), `card` (#f0f0f0), `blue` (#d9ecff) |
| Radius | `$of-radius-*` | `sm` (8px), `card` (10px), `lg` (12px) |
| Gradients | `$of-gradient-*` | `blue`, `accent`, `hero`, `manual` |
| Shadows | `$of-shadow-*` | `card`, `hover`, `primary` |

### Reusable Classes (in `opsflow-global.scss`)

| Class | Usage |
|-------|-------|
| `.of-card` | Card containers — standard bg/border/radius |
| `.of-fade-in-up` | Section entrance animation (opacity 0→1 + translateY) |
| `.of-stagger-item` | Staggered list item entrance (same as above, faster) |

### Mixins (in `opsflow-global.scss`)

| Mixin | Usage |
|-------|-------|
| `@include of-dialog-header` | Dialog header padding/border (via `:deep(.el-dialog__header)`) |
| `@include of-dialog-body` | Dialog body padding |
| `@include of-dialog-footer` | Dialog footer border/padding |
| `@include of-hover-lift` | Card hover: translateY(-1px) + shadow |
| `@include of-hover-shift` | Item hover: translateX(3px) + shadow |
| `@include of-icon-circle($size, $gradient)` | Gradient circle avatar/icon |

## HTML Conventions

- **Class naming:** kebab-case, component-prefixed (e.g. `mycomp-header`, `mycomp-body`)
- **Dialogs:** Always add `class="opsflow-dialog"` to `<el-dialog>` for unified styling
- **Empty state:** `<el-empty :image-size="40" />`
- **Loading:** Use `v-loading` with `element-loading-text`

## Example

```vue
<template>
  <el-dialog v-model="visible" title="Dialog" class="opsflow-dialog">
    <div class="of-fade-in-up">
      <div class="of-card">
        <span>Content</span>
      </div>
    </div>
    <template #footer>
      <el-button @click="visible = false">Cancel</el-button>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
@import '../styles/opsflow-global';

.opsflow-dialog :deep(.el-dialog__header) { @include of-dialog-header; }
.opsflow-dialog :deep(.el-dialog__body) { @include of-dialog-body; }
.opsflow-dialog :deep(.el-dialog__footer) { @include of-dialog-footer; }
</style>
```

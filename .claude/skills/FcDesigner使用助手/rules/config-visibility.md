# config：显隐、菜单与模块

## 要点
- 显隐控制：`showMenuBar`、`showConfig`、`showPreviewBtn`、`showTemplate` 等。
- 菜单与组件：`hiddenMenu`、`hiddenItem`（组件/分组级隐藏，与下方模块开关是两层控制）。

### 常用显隐开关
- `showSaveBtn`、`showPreviewBtn`、`showPrintBtn`
- `showMenuBar`、`showConfig`、`showTemplate`
- `showFormConfig`、`showBaseForm`、`showPropsForm`、`showStyleForm`、`showEventForm`、`showValidateForm`

```ts
const config = {
  showSaveBtn: false,
  showPreviewBtn: true,
  showPrintBtn: false,
};
```

### 隐藏菜单与组件

```ts
const config = {
  hiddenMenu: ['subform'],
  hiddenItem: ['group', 'tree'],
};
```

### 功能模块显隐（与 hiddenMenu 配合）
- 顶部：`showSaveBtn`、`showPreviewBtn`、`showPrintBtn`、`showImportBtn`
- 左侧：`showMenuBar`、`showTemplate`、`showLanguage`、`showJsonPreview`
- 右侧：`showConfig`、`showBaseForm`、`showAdvancedForm`、`showPropsForm` 等
- 交互：`hiddenDragMenu`、`hiddenDragBtn`、`hotKey`、`exitConfirm`

## 关联
- 拖拽与权限：`config-drag-perm.md`
- 表单级 meta：`config-form-meta.md`

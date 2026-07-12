# 设计器原型能力（FcDesigner / formCreate）

## 要点
- `FcDesigner.component(name, component, preview?)`：全局注册或覆盖设计器内预览相关组件。
- `FcDesigner.addMenu(menu, before?)`：全局导入菜单分组。
- `FcDesigner.addDragRule(rule, before?)`：全局导入拖拽规则。
- `FcDesigner.setFormula(formula)`：扩展公式函数。
- `FcDesigner.formCreate` / `designerForm`：运行态与设计态 **form-create** 入口，用于统一注册 `parser`、`component`、`extendApi` 等。

## 关联
- 实例方法列表：`ref-overview.md`

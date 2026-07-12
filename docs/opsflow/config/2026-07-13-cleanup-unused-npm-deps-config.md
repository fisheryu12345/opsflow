# 清理 14 个未使用的 npm 依赖包

> 提交: 0237cea6 | 日期: 2026-07-13
> 涉及 App: opsflow (跨平台基础设施)
> 类型: 配置变更 (依赖清理)

---

## 变更内容

对 `web/package.json` 中全部 63 个依赖包逐一扫描（对照 `web/src/` 229+ 源文件的 import 使用情况），识别并清理了以下未使用的包：

### 删除的 dependencies（12 个）

| 包名 | 原版本 | 未使用原因 |
|------|--------|-----------|
| `@fast-crud/fast-crud` | ^1.19.2 | 仅用 `dict()`/`uiContext`/类型，无 `<fs-crud>` 组件使用 |
| `@fast-crud/fast-extends` | ^1.19.2 | `FsExtendsEditor`/`FsExtendsUploader` 注册但无模板引用 |
| `@fast-crud/ui-element` | ^1.19.2 | 仅 `settings.ts` 中 `app.use(ui)`，无其他引用 |
| `@fast-crud/ui-interface` | ^1.19.2 | 零直接导入（仅传递依赖） |
| `@antv/layout` | ^2.0.0 | `web/src/` 零匹配 |
| `countup.js` | ^2.3.2 | `web/src/` 零 import |
| `echarts-gl` | ^2.0.9 | `web/src/` 零匹配 |
| `echarts-wordcloud` | ^2.1.0 | `web/src/` 零匹配 |
| `jsplumb` | ^2.15.6 | 仅 `types/views.d.ts` 残留类型声明，无运行时使用 |
| `markdown-it` | ^14.1.1 | `web/src/` 零匹配 |
| `print-js` | ^1.6.0 | `web/src/` 零匹配 |
| `splitpanes` | ^3.1.5 | 仅 `types/global.d.ts` 残留 `declare module`，无实际 import |
| `upgrade` | ^1.1.0 | `web/src/` 零匹配 |

### 删除的 devDependencies（1 个）

| 包名 | 原版本 | 未使用原因 |
|------|--------|-----------|
| `@iconify/vue` | ^5.0.1 | `web/src/` 零 import |

### 从 dependencies 移至 devDependencies（3 个）

| 包名 | 原分类 | 新分类 | 原因 |
|------|--------|--------|------|
| `@vitejs/plugin-vue-jsx` | dependencies | devDependencies | Vite 构建插件，非运行时依赖 |
| `autoprefixer` | dependencies | devDependencies | PostCSS 插件，仅 `postcss.config.js` 构建时引用 |
| `postcss` | dependencies | devDependencies | CSS 处理工具，仅构建时使用 |

### 同步修改的源文件（8 个）

| 文件 | 操作 |
|------|------|
| `web/src/settings.ts` | **删除** — 全部 FastCrud 插件注册代码，无其他内容 |
| `web/src/utils/commonCrud.ts` | **删除** — 零引用死代码 |
| `web/src/components/tableSelector/index.vue` | `dict()` 替换为项目已有的 `request()` |
| `web/src/utils/tools.ts` | `uiContext` 替换为 Element Plus `ElNotification` |
| `web/src/views/system/messageCenter/api.ts` | `PageQuery` 等类型导入替换为本地类型别名 |
| `web/src/views/system/config/api.ts` | `UserPageQuery` 等类型导入替换为本地类型别名 |
| `web/src/main.ts` | 移除 `fastCrud` import 和 `.use(fastCrud)` |
| `web/src/assets/style/reset.scss` | 删除 `.fs-crud-container` CSS 规则 |

## 影响的服务

- **前端 dev server + 构建** — `npm install` 后 node_modules 减少 225 个包（含传递依赖）
- 无需重启后端服务

## 部署注意事项

1. 部署前执行 `cd web && npm install` 更新 node_modules
2. 确认生产构建无错误：`npm run build`
3. 无数据库迁移或其他后端变更

## 回退方式

```bash
git revert <commit hash>
cd web && npm install
```

### 关联文档

- 前端架构文档: [04-frontend.md](../architecture/04-frontend.md)

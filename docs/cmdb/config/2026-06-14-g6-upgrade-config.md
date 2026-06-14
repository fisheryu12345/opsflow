# G6 版本升级

> 提交: 4ce858ff | 日期: 2026-06-14
> 涉及 App: cmdb
> 类型: 配置变更

---

## 变更内容

`@antv/g6` 从 `4.8.25` 升级到 `5.1.1`。

对应的导入方式变化：

```js
// 旧 (G6 v4)
import G6 from '@antv/g6'
const graph = new G6.TreeGraph({ ... })
const graph = new G6.Graph({ ... })

// 新 (G6 v5)
import { Graph, Rect, Badge, treeToGraphData, register, ExtensionCategory } from '@antv/g6'
const graph = new Graph({ ... })
```

## 影响的服务

前端 CMDB 拓扑视图页面需重新构建部署。

## 部署注意事项

`npm install` 会自动安装 `@antv/g6@5.1.1`（已在 `package-lock.json` 中锁定）。

## 回退方式

恢复 `package.json` 中 `@antv/g6` 版本为 `4.8.25`，重新运行 `npm install`。

### 关联文档

- 相关功能文档: [拓扑演示数据](features/2026-06-14-topology-demo-data.md)
- 相关架构文档: [G6 v5 迁移重构](architecture/2026-06-14-topology-g6-v5-migration-refactor.md)

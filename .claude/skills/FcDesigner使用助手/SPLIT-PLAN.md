# FcDesigner使用助手 · 拆分方案（对标 vercel-react-best-practices）

本文说明如何借鉴 **`vercel-react-best-practices`** 的拆分思路，改造当前「单文件 `AGENTS.md` + 厚 `SKILL.md`」结构，使 Agent **按需加载规则文件**，同时保留 **`references/types.md`** 的权威类型口径与 **`faq-runtime.md`** 的排障入口。

---

## 一、Vercel 技能可借鉴的点

| 做法 | Vercel 中的形态 | 对本技能的映射 |
|------|-----------------|----------------|
| 薄入口 | `SKILL.md`：何时用、**按优先级分组的类别表**、**规则前缀**、Quick Reference 只列 slug + 一行说明 | `SKILL.md` 只保留路由、优先级、规则索引，大段示例迁出 |
| 一文件一主题 | `rules/async-parallel.md` 等，**可单独加载** | `rules/ref-setrule.md` 等，一条能力一个文件 |
| 命名前缀 | `async-`、`bundle-`、`rerender-` 表达领域 + 检索 | 见下文 **前缀体系** |
| 全文汇编 | `AGENTS.md` = 全量展开（可选：机器生成或手工维护目录链） | `AGENTS.md` 改为 **目录 + 链接** 或保留为「汇编版」二选一 |
| 模板 | （可选，自建） | 单条规则文档结构可按 Vercel 习惯自拟 |

---

## 二、目标结构（建议落地目录）

```text
FcDesigner使用助手/
├── SKILL.md                 # 薄入口：何时用、优先级表、Quick Reference、如何读 rules
├── AGENTS.md                # 二选一：A) 全量汇编  B) 总目录 + 各 rules 链接（推荐 B 降体积）
├── SPLIT-PLAN.md            # 本文件
├── references/
│   ├── types.md             # 不变：TS 权威口径
│   └── faq-runtime.md       # 不变：FAQ
└── rules/
    ├── ref-overview.md      # 实例方法总览、调用时机（原 §2 精华）
    ├── config-visibility.md # showXxx、hiddenXxx、模块显隐（原 §3 一部分）
    ├── config-drag-perm.md  # allowDrag、denyDrag、componentPermission、checkDrag
    ├── config-form-meta.md  # fieldList、formOptions、hiddenFormConfig 等
    ├── extend-menu-component.md # addMenu、addComponent、DragRule 概要（原 §4）
    ├── panel-base-component-rule.md # baseRule、formRule、componentRule、appendConfigData（原 §5）
    ├── default-rule-global.md       # updateDefaultRule、option.global、parser 边界（原 §6）
    ├── event-designer.md      # 设计器事件、api.emit、inject（原 §7 一部分）
    ├── api-message.md         # api.message / api.confirm 跨栈（原 §7.1）
    ├── stack-element-antd.md  # Element vs Antd（原 §8）
    ├── proto-global.md        # FcDesigner.component、setFormula、formCreate 扩展（原 §2.3 + 散点）
    ├── data-save-parse.md     # parseJson、toJson、保存回显（原 §9.24 + faq 交叉）
    └── adv-*.md               # 按需从原 §9.x 拆：preview、print、upload、fetch…（可分批）
```

说明：**不必一次拆满**；可先建 `rules/`，把最常被问的 **config / ref / parseJson** 迁 3～5 个文件验证流程，再批量迁移 §9.x。

---

## 三、前缀体系（对标 async- / bundle-）

| 前缀 | 含义 | 示例 slug |
|------|------|-----------|
| `ref-` | `designer` ref 与实例方法、调用时机 | `ref-overview`、`ref-preview-export` |
| `config-` | `props` / `config` 行为与显隐 | `config-visibility`、`config-drag-perm` |
| `extend-` | 菜单、组件、DragRule 扩展 | `extend-menu-component` |
| `panel-` | 右侧面板、baseRule / componentRule | `panel-base-component-rule` |
| `default-` | 默认值、运行时 global、parser 层级 | `default-rule-global` |
| `event-` | 设计器事件、业务透传 | `event-designer`、`event-emit` |
| `api-` | 运行态 `api.*`（与 form-create 实例相关） | `api-message`、`api-fetch` |
| `data-` | 规则/选项序列化、全局数据、变量 | `data-save-parse`、`data-global-variable` |
| `stack-` | UI 栈差异 | `stack-element-antd` |
| `proto-` | 设计器原型扩展 | `proto-global` |
| `adv-` | 高级/低频：主题、SFC、分步表单等 | `adv-theme`、`adv-step-form` |

与 Vercel 一样：**文件名 = 可检索关键词**，便于 Agent `read_file` 单条加载。

---

## 四、`SKILL.md` 改造后应长什么样（示意）

1. **何时应用**（保留，可略缩）。
2. **规则类别与优先级**（仿 Vercel 表格）：

| 优先级 | 类别 | 典型场景 | 前缀 |
|--------|------|----------|------|
| 高 | 实例与规则读写 | setRule、getJson、parseJson | `ref-`、`data-` |
| 高 | 功能显隐与拖拽权限 | showSaveBtn、denyDrag | `config-` |
| 中 | 扩展与右侧面板 | addMenu、baseRule | `extend-`、`panel-` |
| 中 | 事件与消息 | save、api.message | `event-`、`api-` |
| 中 | 双栈差异 | antd vs element | `stack-` |
| 低 | 高级能力 | 主题、打印、动态组件 | `adv-` |

3. **Quick Reference**：列出 `rules/xxx.md` 与一句话（不贴大段代码）。
4. **如何使用**：先 `types.md` 核对签名 → 再打开对应 `rules/*.md` → FAQ 见 `faq-runtime.md`。
5. **原 SKILL 内嵌的长示例**：迁移到对应 `rules/` 或删除（避免与 AGENTS/rules 三处重复）。

---

## 五、`AGENTS.md` 两种演进策略

**策略 A（汇编版，贴近 Vercel 当前 `AGENTS.md`）**  
- `AGENTS.md` 仍为「一次性加载」的全文，内容由 `rules/*.md` **拼接或复制**维护。  
- 优点：兼容「只读 AGENTS」的旧习惯。  
- 缺点：体积大，易与 `rules` 双份不一致。

**策略 B（目录版，推荐）**  
- `AGENTS.md` 只保留：**摘要 + 完整目录 + 每节指向 `rules/xxx.md` 的链接 + types/faq 说明**。  
- 细节只在 `rules/`。  
- 优点：单一事实来源，和 Vercel「读单条 rule 文件」一致。  
- 缺点：Agent 需习惯「点进 rules」。

**当前落地**：**策略 A** — `AGENTS.md` 保留**完整全文**（与历史一致）；`rules/` 为按主题拆分的**并行**材料，便于 Agent `read_file` 单条加载，与 AGENTS 对应章节内容一致时需以 **`references/types.md`** 统一口径（避免双份长期漂移可定期对账）。

---

## 六、与现有 `references` 的分工

| 文件 | 角色 | 是否参与拆分 |
|------|------|----------------|
| `references/types.md` | 权威类型，冲突以它为准 | **不拆**；`rules/*.md` 中示例与 types 冲突时以 types 更正 |
| `references/faq-runtime.md` | 排障、与安装助手交叉 | **不拆**；`rules` 里业务规则只写「正确用法」，故障见 faq |

---

## 七、迁移步骤（建议分阶段）

1. **基建**：建立 `rules/` 与各主题 `*.md`。**已完成**
2. **试点**：从 `AGENTS.md` 抽出 **§3 显隐**、**§2 方法总览**、**parseJson 段落** 各做 1 个 `rules/config-*.md`、`rules/ref-*.md`、`rules/data-save-parse.md`。**已完成**（并扩展为全套 `rules/*.md` + `adv-code-snippets.md`）
3. **改 SKILL**：按第四节重写「能力优先级表 + Quick Reference」，删除 SKILL 内重复长代码块。**已完成**
4. **AGENTS 形态**：保留全文汇编（策略 A），**不**收缩为仅目录。**已按项目要求维持完整 `AGENTS.md`**
5. **§9.x 大段示例**：汇编至 `rules/adv-code-snippets.md`。**已完成**；若后续需再按子主题拆 `adv-*.md` 可分批进行。
6. **回归**：用 `FcDesigner使用助手/evals/evals.json` 抽样跑几条，确认仍能命中 `rules` 或 `types`。**待人工抽样**

---

## 八、与 Vercel 的刻意不同

- **FcDesigner** 强依赖 **`types.md`**，Vercel 规则多为模式说明；因此每条 `rules/*.md` 末尾加一句：**「字段名以 `references/types.md` 为准」**。
- **安装/二开** 不归本技能；`SKILL.md` 保留指向 **安装助手**、**二开助手** 的一句分流即可（已有）。

---

## 九、验收标准

- [x] 新同学只看 `SKILL.md` 能在 1 分钟内定位到应打开的 `rules/*.md`。
- [x] 任意业务问题可 **单次加载 1～2 个 rule 文件** + `types.md`，或直接通读完整 `AGENTS.md`。
- [x] `types.md` / `faq-runtime.md` 仍保持唯一权威；正文与示例冲突时以 types 为准。

---

**文档版本**：与 `SKILL.md` metadata 同步迭代；重大结构调整时更新本文件「迁移步骤」勾选状态。

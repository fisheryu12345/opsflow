# FormCreate Skills

本目录包含 **5 个 Agent Skills**，用于你在做业务开发时，把「表单需求」快速落到 **可运行代码 / 可维护配置 / 可复用改造点** 上（基于 **FormCreate（表单渲染）** 与 **FcDesigner（可视化设计器）**）。它的目标不是讲概念，而是让 AI 在你的技术栈里直接产出能落地的实现。

---

## 我该用哪个 skill（按业务问题选）

先判断你要落地的业务需求属于哪一类：

| 你的问题 | 用哪个 skill |
|---------|-------------|
| 要装哪个 npm 包、main 里怎么 `use`、样式不生效 | **FormCreate安装助手** |
| 已能渲染表单，要写 `rule`/`option`、联动、校验、`parseJson`/`toJson` | **FormCreate使用助手** |
| 设计器怎么装、白屏、Pro dist/CDN | **FcDesigner安装助手** |
| 设计器 `ref`、`setRule`、`getJson`、菜单/拖拽/预览 | **FcDesigner使用助手** |
| 要改设计器源码、DragRule、升级合并仓库 | **FcDesigner二开助手** |

---

## 五个 skill 分别做什么

| 目录名 | 一句话 |
|--------|--------|
| `FormCreate安装助手` | 运行态渲染器的安装、包名、挂载与常见排错。 |
| `FormCreate使用助手` | 运行态：`rule`/`option`/`api`、联动校验、序列化、各 UI 栈差异；入口见 `SKILL.md`，全文见 `AGENTS.md`，类型见 `references/types.md`。 |
| `FcDesigner安装助手` | 设计器包怎么装、资源怎么引、白屏类问题。 |
| `FcDesigner使用助手` | 设计器已集成后的 `ref`、配置、扩展菜单与规则；权威类型见 `references/types.md`。 |
| `FcDesigner二开助手` | 源码级二开：内置组件、默认规则、升级合并等。 |

每个目录内通常包含：

- `SKILL.md`：简介、何时用、快速索引（优先读这个）
- `AGENTS.md`：完整说明（需要细查时再看）
- `references/`、`rules/`（若有）：专题与拆分文档

---

## 怎么在业务项目里用

### 方式 A：在 Cursor 里用

1. 解压你拿到的 `skills.zip`，把整个 **skills 内容**放到项目根目录下的 **`.cursor/skills/`**（与本文档同级的是各个 `*助手` 文件夹）。
2. 重载窗口或重新打开项目，让 Cursor 重新索引。

### 方式 B：在 Claude Code 里用

Claude Code 通过 **`.claude/skills/<skill 名称>/SKILL.md`** 识别 skill（名称一般与 `SKILL.md` 里 `name` 字段一致）。

1. 在项目中创建 `.claude/skills/`。
2. 将本仓库里每个助手文件夹 **整份复制**到 `.claude/skills/` 下，并保持目录名与 skill 名称一致，例如：
   - `.claude/skills/FormCreate使用助手/SKILL.md`
   - 同目录保留 `AGENTS.md`、`references/`、`rules/` 等，避免文档内相对链接失效。

## 怎么提需求

导入后会在相关话题下自动选用；也可在对话里 **手动调用**：输入 `/技能名`，然后直接描述你的业务目标（页面/字段/接口/权限/保存回显/预览等）。一般情况下，AI 会输出能直接复制的代码与配置；你只需要补充你的 UI 栈、Vue 版本、以及已有的入口代码或报错信息即可。

### 示例

#### 1) 运行态业务：级联选择 + 远程选项

```text
/FormCreate使用助手
我要做一个「省/市/区」三级联动表单（Vue3 + Ant Design Vue），请你直接输出一个可运行的 SFC：用 form-create 渲染 rule/option，并用 control/computed 实现远程加载 options、联动清空下级字段、loading 禁用与失败提示（不要伪代码，复制即可跑）。
```

#### 2) 运行态业务：草稿保存 + 回显 + 版本兼容

```text
/FormCreate使用助手
我要实现「保存草稿 / 打开草稿继续填写」，请你直接给出最小可用实现：前端用 toJson/parseJson 的保存与回显代码 + 后端接口 payload 示例，并说明 schema 升级（字段增删）时的兼容策略，以及哪些内容不应该入库（例如函数/事件）。
```

#### 3) 接入业务：新项目把 form-create 跑起来

```text
/FormCreate安装助手
我在新项目里用 Vue3 + Element Plus，从 0 接入 form-create 并渲染一个最小表单页；请你直接输出我能照抄的安装命令、main.ts 完整入口代码、一个最小页面组件示例，以及样式应该在哪里引入。
```

#### 4) 设计态业务：表单模板中心（导入/导出/预览）

```text
/FcDesigner使用助手
我要做一个「表单模板中心」页面；请你直接写一个可运行的 SFC：包含 fc-designer、ref 获取、导出模板（getJson 后调接口保存，携带模板名与版本号）、导入模板（接口取回后 setRule 回显）以及打开预览，并把接口 payload 示例与错误提示一起写全。
```

#### 5) 设计态业务：权限与可用组件控制

```text
/FcDesigner使用助手
我要按「角色」限制设计器能力：访客只能预览不能编辑；运营可编辑但不能拖拽“上传/富文本”；管理员全开放；请你直接给出可复制的 config/初始化代码，并同时给出设计态限制（菜单/拖拽/面板）与运行态兜底限制（提交校验/字段过滤）分别应该落在哪些入口、怎么写。
```

#### 6) 接入业务：设计器白屏快速恢复

```text
/FcDesigner安装助手
我接入设计器后出现白屏/样式丢失/依赖报错；我会贴入口代码、控制台报错和资源加载情况，请你按排查清单逐项定位原因，并给出最终可运行的入口修复方案（包含依赖安装命令与 import/样式/路径的具体改动）。
```

#### 7) 二开业务：公司规范内置化

```text
/FcDesigner二开助手
我要把公司的表单规范内置到设计器：所有 input 默认加 maxlength=50、手机号字段默认加正则校验、所有字段默认带 `effect: { audit: true }`；请你指出需要修改的源码文件与关键位置，并直接给出最小补丁（代码片段或 patch）和验证步骤，同时说明后续升级合并最容易冲突的点与维护策略。
```

# 开源版 FcDesigner：npm 多栈接入参考

本文件与 `AGENTS.md` **§11** 配套：`AGENTS.md` 保留选型表与安装命令速查；此处补充**按场景阅读清单**、**完整示例片段**、**CDN 要点与勘误**。路径相对于 **FcDesigner安装助手** 目录；不依赖 skill 外的仓库名或交付包内 `.md` 文件名。

---

## 一、各接入场景的独立阅读 Todo

每类场景执行：`通读` → `提炼栈与版本` → `对照 §11 选型表` → `记录与交付侧说明的差异`（若有）

### 1. Vue2 + Element UI（PC）

- [ ] 确认目标：Vue **2.7+**、**Element UI**、**@form-create/designer@^1**
- [ ] 记录依赖：`@form-create/element-ui@^2.7`、`element-ui`
- [ ] 核对入口：`Vue.use(ELEMENT)` → `Vue.use(FcDesigner)` → `Vue.use(FcDesigner.formCreate)`
- [ ] 若 Vue 版本低于 2.7：规划升级 `vue@^2.7`
- [ ] 页面标签：`<fc-designer ref="designer" height="100vh" />`

### 2. Vue3 + Element Plus（PC）

- [ ] 确认目标：Vue3、**Element Plus**、**@form-create/designer@^3**
- [ ] 记录依赖：`@form-create/element-ui@^3`（渲染器包名）、`element-plus`；**form-create ≥ 3.2.18**
- [ ] 核对入口：`app.use(ElementPlus)` → `app.use(FcDesigner)` → `app.use(FcDesigner.formCreate)`
- [ ] CDN 注意：`@next` 与 `@form-create/element-ui` 的对应关系以项目为准

### 3. Vue3 + Ant Design Vue（PC）

- [ ] 与 Element 栈对照：Antd 路线须使用 **`@form-create/ant-design-vue`**，勿误用 `@form-create/element-ui`
- [ ] 设计器包：**`@form-create/antd-designer@^3`**
- [ ] 依赖：`ant-design-vue`、`@form-create/ant-design-vue@^3`；**form-create ≥ 3.2.18**
- [ ] 样式：`ant-design-vue/dist/reset.css`（按项目 ant-design-vue 主版本选择）
- [ ] **勿**在 Antd 路线中写 Element Plus 挂载

### 4. Vue3 + 移动端设计器（Vant 栈）

- [ ] 设计器包：`@form-create/vant-designer@^3`
- [ ] 双栈：左侧设计器 UI 仍用 **Element Plus**；**Vant** 用于移动端预览/渲染
- [ ] 渲染器：`@form-create/element-ui@^3`（PC 侧）+ `@form-create/vant@^3`（移动侧）；**form-create ≥ 3.2.14**
- [ ] 组件名：**`<fc-designer-mobile>`**；运行时与 PC 对照：`fc-designer` / `form-create` 与 `fc-designer-mobile` / `form-create-mobile` 按场景选用
- [ ] 挂载顺序：`app.use(ElementPlus)` → `app.use(vant)` → `app.use(FcDesignerMobile)` → `app.use(FcDesignerMobile.formCreate)`

### 5. 源码集成（自仓库拷贝，二开）

- [ ] 归属**二开/源码改造**：与 npm 安装并列的另一种接入方式
- [ ] 分支与目录：见 **`FcDesigner二开助手/references/source-repository.md`**（避免在本文件重复粘贴）

---

## 二、合并对照（与 §11 一致，便于单文件加载）

| 场景 | Vue | UI | 设计器包 | 渲染器与其它 |
|------|-----|-----|----------|----------------|
| PC + Element | ≥2.7 | Element UI | `@form-create/designer@^1` | `@form-create/element-ui@^2.7` + `element-ui` |
| PC + Element Plus | 3 | Element Plus | `@form-create/designer@^3` | `@form-create/element-ui@^3` + `element-plus`；**≥3.2.18** |
| PC + Ant Design Vue | 3 | ant-design-vue | `@form-create/antd-designer@^3` | `@form-create/ant-design-vue@^3` + `ant-design-vue`；**≥3.2.18** |
| 移动端 | 3 | Element Plus + Vant | `@form-create/vant-designer@^3` | `@form-create/element-ui@^3`、`@form-create/vant@^3`、`element-plus`、`vant`；**≥3.2.14** |

---

## 三、Node 引入完整片段（按栈选一段，勿混写）

### Vue2 + Element UI（PC）

```js
import Vue from 'vue';
import FcDesigner from '@form-create/designer';
import ELEMENT from 'element-ui';
import 'element-ui/lib/theme-chalk/index.css';

Vue.use(ELEMENT);
Vue.use(FcDesigner);
Vue.use(FcDesigner.formCreate);
```

### Vue3 + Element Plus（PC）

```js
import { createApp } from 'vue';
import FcDesigner from '@form-create/designer';
import ElementPlus from 'element-plus';
import 'element-plus/dist/index.css';

const app = createApp(App);
app.use(ElementPlus);
app.use(FcDesigner);
app.use(FcDesigner.formCreate);
app.mount('#app');
```

### Vue3 + Ant Design Vue（PC）

```js
import { createApp } from 'vue';
import FcDesigner from '@form-create/antd-designer';
import antd from 'ant-design-vue';
import 'ant-design-vue/dist/reset.css';

const app = createApp(App);
app.use(antd);
app.use(FcDesigner);
app.use(FcDesigner.formCreate);
app.mount('#app');
```

### Vue3 + 移动端设计器

```js
import { createApp } from 'vue';
import FcDesignerMobile from '@form-create/vant-designer';
import ELEMENT from 'element-plus';
import vant from 'vant';
import 'vant/lib/index.css';
import 'element-plus/dist/index.css';

const app = createApp(App);
app.use(ELEMENT);
app.use(vant);
app.use(FcDesignerMobile);
app.use(FcDesignerMobile.formCreate);
app.mount('#app');
```

### 页面模板（PC / 移动）

```vue
<!-- PC -->
<fc-designer ref="designer" height="100vh" />

<!-- 移动端 -->
<fc-designer-mobile ref="designer" height="100vh" />
```

---

## 四、CDN 要点与勘误

1. **顺序**：先 Vue，再 UI（Element Plus / Element UI / ant-design-vue），再 `@form-create/*` 渲染器 UMD，再 designer UMD，最后 `app.use` 挂载。
2. **Vue3 + Element Plus（PC）**：典型组合为 `vue` + `element-plus` + `@form-create/element-ui@next` 的 `form-create.min.js` + `@form-create/designer@next` 的 `index.umd.js`。
3. **Ant Design Vue 纯 PC**：仅需 ant-design-vue + `@form-create/ant-design-vue` + `@form-create/antd-designer`；**若某段 CDN 示例同时引入 Vant，多为完整包或示例混排，按「仅 PC」时应去掉 Vant。**
4. **移动端 CDN**：需同时引入 Element Plus 与 Vant 的 CSS/JS，以及 `element-ui` 包名在 Vue3 下对应 `@form-create/element-ui@next` 与 `@form-create/vant@next`（以实际包版本为准）。

---

## 五、数据结构（安装阶段最小集）

- `ref`：设计器实例，用于后续 `setRule` / `getJson` 等（详见 **FcDesigner使用助手**）。
- `height`：设计器容器高度（如 `100vh`）。
- 初始化：仅在应用挂载完成后再调用 `ref` 上方法。

---

## 六、与另两个 skill 的职责边界

- **安装接入**（本技能 + `AGENTS.md` §11）：包名、挂载顺序、CDN、版本。
- **使用**：`ref` 方法、`config`、保存回显（见 **FcDesigner使用助手**）。
- **二开**：从 `form-create-designer` 仓库拷贝源码目录、分支选择、本地 `import`（见 **FcDesigner二开助手/references/source-repository.md**）。

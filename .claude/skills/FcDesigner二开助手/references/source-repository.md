# form-create-designer 源码仓库集成

本文件说明「源码集成」主题下的仓库分支与目录选择，与 **FcDesigner安装助手** `AGENTS.md` §4.2「源码集成」互补：安装技能给流程；此处给**仓库分支、源码路径、目录结构**。

路径描述仅使用「业务项目内」相对位置（如 `src/components/FcDesigner`），不依赖本 skill 外的目录。

---

## 一、获取源码

```bash
git clone https://github.com/xaboy/form-create-designer.git
cd form-create-designer
npm install
```

---

## 二、版本与源码路径选择

| 项目类型 | 分支 | 源码路径（仓库内） | UI 依赖 |
|----------|------|---------------------|---------|
| Vue 2 | master | `form-create-designer/src` | element-ui |
| Vue 3 | next | `packages/element-ui/src` | element-plus |
| Vue 3 | next | `packages/ant-design-vue/src` | ant-design-vue |
| Vue 3 | next | `packages/vant/src` | vant |

按业务栈选择**同一套**目录（Element / Antd / Vant 勿混目录）。

---

## 三、仓库内核心结构（集成时可对照）

```
src/
├── components/    # 设计器组件
├── config/        # 配置
├── utils/         # 工具
├── index.js       # 入口
```

---

## 四、集成到业务项目

1. 将选中目录复制到业务项目，例如 `src/components/FcDesigner/`（与 `AGENTS.md` 建议一致）。
2. 将源码包内 `package.json` 的 `dependencies` 合并到业务项目 `package.json`。
3. 重新执行 `npm install` 或 `pnpm install`。

### Vue 2 入口示例

```js
import Vue from 'vue';
import FcDesigner from '@/components/FcDesigner';

Vue.use(FcDesigner);
Vue.use(FcDesigner.formCreate);
```

### Vue 3 入口示例

```js
import { createApp } from 'vue';
import FcDesigner from '@/components/FcDesigner';

const app = createApp(App);
app.use(FcDesigner);
app.use(FcDesigner.formCreate);
app.mount('#app');
```

### 组件使用

```vue
<template>
  <fc-designer ref="designer" />
</template>

<script>
export default {
  mounted() {
    console.log(this.$refs.designer);
  },
};
</script>
```

---

## 五、与 npm 包的关系

- **npm**：`@form-create/designer` 等，升级跟随 registry。
- **源码**：可深度改 DragRule、组件、打包；升级需与上游仓库 diff 合并（见 **FcDesigner二开助手** `AGENTS.md` 迁移章节）。

# config：拖拽、权限与安全行为

## 拖拽
- 全局校验：`checkDrag(drag) => boolean`
- 允许拖入：`allowDrag`
- 禁止拖入：`denyDrag`

```ts
const config = {
  allowDrag: {
    group: { item: ['input', 'select'], menu: ['main'] },
  },
  denyDrag: {
    table: { item: ['upload'], menu: ['aide'] },
  },
};
```

## 组件权限
按 `field` / `name` / `tag` / `id` 限制删除、复制、移动、面板权限等：

```ts
const config = {
  componentPermission: [
    {
      tag: 'input',
      permission: {
        delete: false,
        copy: false,
        move: false,
        event: false,
        validate: false,
      },
    },
  ],
};
```

## 行为与安全
- `beforeRemoveRule`、`beforeActiveRule`
- `hotKey`、`exitConfirm`、`checkFieldUnique`

```ts
const config = {
  hotKey: true,
  exitConfirm: true,
  checkFieldUnique: true,
  beforeRemoveRule: ({ rule }) => (rule?.field === 'lockedField' ? false : undefined),
};
```

## 关联
- 显隐：`config-visibility.md`

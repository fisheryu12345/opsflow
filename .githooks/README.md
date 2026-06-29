# Git Hooks

## 安装

```bash
git config core.hooksPath .githooks
```

## 可用钩子

| Hook | 触发时机 | 作用 |
|------|---------|------|
| `pre-commit` | `git commit` | Python 语法检查（防止 `},` 等语法错误）、新插件 name_en 检查 |
| `pre-push` | `git push` | 运行核心测试（opsflow 核心测试套件） |

## 跳过钩子（紧急情况）

```bash
git commit --no-verify      # 跳过 pre-commit
git push --no-verify        # 跳过 pre-push
```

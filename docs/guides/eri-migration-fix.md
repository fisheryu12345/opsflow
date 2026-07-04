# eri.0006 Migration 修复说明

## 背景

`bamboo-pipeline` 包（v4.0.3）中的 `pipeline.eri.migrations.0006` 使用了 `RenameIndex(old_fields=...)`。

这个操作在 **MySQL 上正常**（旧索引已存在），但在 **SQLite 内存库**（测试环境默认）上失败，因为旧索引从未创建过。导致所有 Django 测试无法运行。

## 修复方法

修改 `pipeline/eri/migrations/0006_rename_executionhistory_...py`：

```python
# 改前
migrations.RenameIndex(
    model_name='executionhistory',
    new_name='eri_executi_node_id_8e4fb0_idx',
    old_fields=('node_id', 'loop'),
),

# 改后
migrations.AddIndex(
    model_name='executionhistory',
    index=models.Index(fields=['node_id', 'loop'], name='eri_executi_node_id_8e4fb0_idx'),
),
```

## 重新安装后需重新修复

`pip install` 或升级 `bamboo-pipeline` 后，此文件会被覆盖还原。修复步骤：

```bash
# 1. 确认版本
pip show bamboo-pipeline | grep Version

# 2. 打开 migration 文件
# .venv/Lib/site-packages/pipeline/eri/migrations/
# 0006_rename_executionhistory_node_id_loop_eri_executi_node_id_8e4fb0_idx_and_more.py

# 3. 编辑两处：
#    - from django.db import migrations → from django.db import migrations, models
#    - 两个 RenameIndex → AddIndex（详见文件头部注释）
```

## 影响范围

| 环境 | 影响 |
|------|------|
| 生产 MySQL | 无影响（eri.0006 已跑过，不会再重跑） |
| 测试 SQLite | 修复前全断，修复后正常 |
| 新环境搭建 | 需要先修复才能跑测试 |

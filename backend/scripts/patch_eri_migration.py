#!/usr/bin/env python
"""
bamboo-pipeline eri.0006 migration SQLite 兼容补丁

bamboo-pipeline 4.0.3 的 eri migration 0006 使用了 ``RenameIndex(old_fields=...)``，
在 MySQL 上正常（旧索引已存在），但在 SQLite 内存数据库（python manage.py test）
上失败，因为旧索引从未创建过。

此脚本将两处 ``RenameIndex`` 替换为 ``AddIndex``，并在文件头部加上说明注释。

用法::

    python scripts/patch_eri_migration.py

支持通过 ``--path`` 指定特定路径（如需修补其他虚拟环境）。
"""

import argparse
import re
import sys
from pathlib import Path


def find_migration_path():
    """查找 eri migration 0006 的路径"""
    # 当前 venv 中查找
    candidates = _find_migrations_recursive(Path(sys.prefix))

    if candidates:
        return candidates[0]

    print(
        "[ERROR] 未找到 pipeline/eri/migrations/0006_*\n"
        "   请手动指定路径: python patch_eri_migration.py --path <site-packages>/pipeline/eri/migrations/0006_*.py"
    )
    return None


def patch_file(path):
    """对指定 migration 应用 RenameIndex → AddIndex 补丁"""
    path = Path(path)
    if not path.exists():
        print(f"[ERROR] 文件不存在: {path}")
        return False

    original = path.read_text(encoding="utf-8")

    # 检查是否已打补丁（检测 migrations.RenameIndex( 函数调用，而非注释中的文字）
    if "migrations.RenameIndex(" not in original:
        print(f"[OK] 补丁已存在，跳过: {path}")
        return True

    # 1. 修复 import（加上 models）
    patched = original.replace(
        "from django.db import migrations\n",
        "from django.db import migrations, models\n",
    )

    # 2. 替换第一个 RenameIndex → AddIndex（executionhistory）
    patched = patched.replace(
        """        migrations.RenameIndex(
            model_name='executionhistory',
            new_name='eri_executi_node_id_8e4fb0_idx',
            old_fields=('node_id', 'loop'),
        ),""",
        """        migrations.AddIndex(
            model_name='executionhistory',
            index=models.Index(fields=['node_id', 'loop'], name='eri_executi_node_id_8e4fb0_idx'),
        ),""",
    )

    # 3. 替换第二个 RenameIndex → AddIndex（logentry）
    patched = patched.replace(
        """        migrations.RenameIndex(
            model_name='logentry',
            new_name='eri_logentr_node_id_adc7e5_idx',
            old_fields=('node_id', 'loop'),
        ),""",
        """        migrations.AddIndex(
            model_name='logentry',
            index=models.Index(fields=['node_id', 'loop'], name='eri_logentr_node_id_adc7e5_idx'),
        ),""",
    )

    if patched == original:
        # 可能是不同版本的 migration，格式有差异
        # 改用正则匹配更通用的模式
        patched = _regex_patch(original)

    if patched == original:
        print(
            f"[ERROR] 未找到需要替换的 RenameIndex 模式\n"
            f"   文件: {path}"
        )
        print("   请检查文件内容，可能已手动修复或版本不同")
        return False

    # 写回文件
    path.write_text(patched, encoding="utf-8")
    print(f"[OK] 补丁已应用到: {path}")
    return True


def _regex_patch(text):
    """用正则替换更灵活的 RenameIndex → AddIndex 模式"""
    # 替换 import
    text = re.sub(
        r'^from django\.db import migrations$',
        'from django.db import migrations, models',
        text,
        flags=re.MULTILINE,
    )
    # 替换 RenameIndex
    text = re.sub(
        r'migrations\.RenameIndex\(\s*model_name=\'([^\']+)\'\s*,\s*new_name=\'([^\']+)\'\s*,\s*old_fields=\([^)]+\)\s*\),',
        r"migrations.AddIndex(\n            model_name='\1',\n            index=models.Index(fields=['node_id', 'loop'], name='\2'),\n        ),",
        text,
    )
    return text


def _find_migrations_recursive(root):
    """安全递归查找 eri migration 文件"""
    results = []
    try:
        for p in root.rglob("pipeline/eri/migrations/0006_*"):
            if p.name.endswith(".py") and not p.name.startswith("__"):
                results.append(p)
    except (OSError, FileNotFoundError, PermissionError):
        pass
    return results


def main():
    parser = argparse.ArgumentParser(description="bamboo-pipeline eri migration SQLite 兼容补丁")
    parser.add_argument(
        "--path",
        help="指定 eri migration 0006 的路径",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="修补所有找到的 migration 副本（跨虚拟环境）",
    )
    args = parser.parse_args()

    if args.path:
        success = patch_file(args.path)
        sys.exit(0 if success else 1)

    # 查找所有副本
    candidates = _find_migrations_recursive(Path(sys.prefix))

    # 去重
    seen = set()
    unique_candidates = []
    for p in candidates:
        resolved = str(p.resolve())
        if resolved not in seen:
            seen.add(resolved)
            unique_candidates.append(p)

    if not unique_candidates:
        print(f"[ERROR] 未找到 pipeline/eri/migrations/0006_*")
        sys.exit(1)

    if args.all:
        successes = [patch_file(p) for p in unique_candidates]
        sys.exit(0 if all(successes) else 1)
    else:
        target = unique_candidates[0]
        print(f"找到 {len(unique_candidates)} 个 eri migration:")
        for p in unique_candidates:
            print(f"  {p}")
        print(f"\n修补: {target}")
        success = patch_file(target)
        if len(unique_candidates) > 1:
            print(
                f"\n[HINT] 共找到 {len(unique_candidates)} 个副本。"
                f"使用 --all 修补全部，或 --path 指定具体路径"
            )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

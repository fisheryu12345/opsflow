#!/usr/bin/env python
"""
bamboo-pipeline Django 5.x 兼容补丁

bamboo-pipeline 4.0.2 的 Meta 类使用了 Django 5.x 中已移除的
``index_together``。此脚本修补 site-packages 中的 models.py。

用法::

    python scripts/patch_bamboo_pipeline.py

运行后重新启动 Django 即可。
"""

import re
import sys
from pathlib import Path


def patch_eri_models():
    """将 site-packages 中 pipeline/eri/models.py 的 index_together 替换为 indexes"""
    try:
        import pipeline.eri.models as m
        path = Path(m.__file__)
    except (ImportError, AttributeError):
        print("❌ pipeline.eri.models 未找到，请确认 bamboo-pipeline 已安装")
        return False

    original = path.read_text(encoding="utf-8")

    # 检查是否已打补丁
    if "indexes = [" in original:
        print("✅ 补丁已存在，无需修改")
        return True

    # 替换 index_together
    patched = re.sub(
        r'(\s+)index_together\s*=\s*\["node_id",\s*"loop"\]',
        r'\1indexes = [\n\1    models.Index(fields=["node_id", "loop"]),\n\1]',
        original,
    )

    if patched == original:
        print("❌ 未找到需要替换的 index_together 模式，补丁失败")
        print("   请检查 pipeline/eri/models.py 内容")
        return False

    # 确保 models 已导入（需要添加 import models 如果还没有）
    if "from django.db import models" not in patched:
        print("⚠️  from django.db import models 未找到，跳过 models.Index 兼容检查")

    path.write_text(patched, encoding="utf-8")
    print(f"✅ 补丁已应用到: {path}")
    return True


if __name__ == "__main__":
    success = patch_eri_models()
    sys.exit(0 if success else 1)

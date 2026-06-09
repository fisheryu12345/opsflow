#!/usr/bin/env python
"""
bamboo-pipeline Django 5.x 兼容补丁

bamboo-pipeline 4.0.2 的 Meta 类使用了 Django 5.x 中已移除的
``index_together``。此脚本通过文本替换修补 site-packages 中的 models.py。

用法::

    python scripts/patch_bamboo_pipeline.py

支持通过 ``python scripts/patch_bamboo_pipeline.py --path <path>``
指定特定 site-packages 路径（如需修补其他虚拟环境）。
"""

import argparse
import re
import sys
from pathlib import Path


def find_eri_models_path():
    """查找 pipeline/eri/models.py 的路径"""
    # 尝试通过导入找到路径
    try:
        import pipeline.eri.models as m
        return Path(m.__file__)
    except (ImportError, AttributeError):
        pass

    # 回退：搜索常见 site-packages 路径
    candidates = list(Path(sys.prefix).rglob("pipeline/eri/models.py"))
    if candidates:
        return candidates[0]

    print(
        "❌ 未找到 pipeline/eri/models.py\n"
        "   请手动指定路径: python patch_bamboo_pipeline.py --path <site-packages>/pipeline/eri/models.py"
    )
    return None


def patch_file(path):
    """对指定文件应用 index_together → indexes 补丁"""
    path = Path(path)
    if not path.exists():
        print(f"❌ 文件不存在: {path}")
        return False

    original = path.read_text(encoding="utf-8")

    # 检查是否已打补丁
    if "indexes = [" in original and "index_together" not in original:
        print(f"✅ 补丁已存在，跳过: {path}")
        return True

    # 确保 from django.db import models 存在
    has_models_import = "from django.db import models" in original

    # 替换 index_together
    patched = re.sub(
        r'(\s+)index_together\s*=\s*\["node_id",\s*"loop"\]',
        lambda m: (
            f'{m.group(1)}indexes = [\n'
            f'{m.group(1)}    models.Index(fields=["node_id", "loop"]),\n'
            f'{m.group(1)}]'
        ),
        original,
    )

    if patched == original:
        print(
            f"❌ 未找到需要替换的 index_together 模式\n"
            f"   文件: {path}"
        )
        print("   请检查文件内容，可能已手动修复")
        return False

    if not has_models_import:
        print("⚠️  注意: 文件中未找到 from django.db import models，补丁已应用但可能不完整")

    # 写回文件
    path.write_text(patched, encoding="utf-8")
    print(f"✅ 补丁已应用到: {path}")
    return True


def _find_models_recursive(root):
    """安全递归查找 pipeline/eri/models.py，跳过无法访问的目录"""
    results = []
    try:
        for p in root.rglob("pipeline/eri/models.py"):
            results.append(p)
    except (OSError, FileNotFoundError, PermissionError):
        pass
    return results


def main():
    parser = argparse.ArgumentParser(description="bamboo-pipeline Django 5.x 兼容补丁")
    parser.add_argument(
        "--path",
        help="指定 pipeline/eri/models.py 的路径（自动查找所有 venv 中的文件）",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="修补所有找到的 pipeline/eri/models.py 副本（跨虚拟环境）",
    )
    args = parser.parse_args()

    if args.path:
        success = patch_file(args.path)
        sys.exit(0 if success else 1)

    # 查找所有副本
    candidates = _find_models_recursive(Path(sys.prefix))
    # 也查找其他常见 venv 位置
    for venv_root in [
        Path(sys.prefix).parent,  # 当前 venv 的父目录
        Path.home() / ".venvs",
    ]:
        if venv_root.exists():
            candidates.extend(_find_models_recursive(venv_root))

    # 去重
    seen = set()
    unique_candidates = []
    for p in candidates:
        resolved = str(p.resolve())
        if resolved not in seen:
            seen.add(resolved)
            unique_candidates.append(p)

    if not unique_candidates:
        print(f"❌ 未找到 pipeline/eri/models.py")
        sys.exit(1)

    if args.all:
        # 修补所有副本
        successes = [patch_file(p) for p in unique_candidates]
        sys.exit(0 if all(successes) else 1)
    else:
        # 仅修补第一个找到的
        print(f"找到 {len(unique_candidates)} 个 pipeline/eri/models.py:")
        for p in unique_candidates:
            print(f"  {p}")
        target = unique_candidates[0]
        print(f"\n修补: {target}")
        success = patch_file(target)
        if len(unique_candidates) > 1:
            print(
                f"\n💡 共找到 {len(unique_candidates)} 个副本。"
                f"使用 --all 修补全部，或 --path 指定具体路径"
            )
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

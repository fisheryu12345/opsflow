"""原子注册中心 — 扫描 ansible_atoms/atoms/*/meta.json 并管理原子元数据"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# 默认查找路径（相对于项目根）
DEFAULT_ATOMS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'ansible_atoms')


@dataclass
class AtomMeta:
    name: str
    description: str = ''
    risk_level: str = 'low'
    group: str = 'action'
    component_code: str = ''
    inputs: list = field(default_factory=list)
    outputs: list = field(default_factory=list)
    rollback: Optional[str] = None
    dependencies: list = field(default_factory=list)
    roles_path: str = ''


# 全局注册表
ATOM_REGISTRY: dict[str, AtomMeta] = {}


def scan_atoms(atoms_dir: str | None = None) -> None:
    """扫描 ansible_atoms/atoms/*/meta.json，填充 ATOM_REGISTRY"""
    base_dir = atoms_dir or DEFAULT_ATOMS_DIR
    atoms_path = os.path.join(base_dir, 'atoms')
    if not os.path.isdir(atoms_path):
        logger.warning(f"原子目录不存在: {atoms_path}")
        return

    count = 0
    for entry in sorted(os.listdir(atoms_path)):
        meta_path = os.path.join(atoms_path, entry, 'meta.json')
        if not os.path.isfile(meta_path):
            continue
        try:
            with open(meta_path, 'r', encoding='utf-8') as f:
                raw = json.load(f)
            meta = AtomMeta(
                name=raw['name'],
                description=raw.get('description', ''),
                risk_level=raw.get('risk_level', 'low'),
                group=raw.get('group', 'action'),
                component_code=raw.get('component_code', f"opsflow_{raw['name']}"),
                inputs=raw.get('inputs', []),
                outputs=raw.get('outputs', []),
                rollback=raw.get('rollback'),
                dependencies=raw.get('dependencies', []),
                roles_path=os.path.join(atoms_path, entry),
            )
            ATOM_REGISTRY[meta.name] = meta
            count += 1
        except Exception as e:
            logger.error(f"加载原子 meta.json 失败 {meta_path}: {e}")

    logger.info(f"原子注册完成: 共 {count} 个原子")


def get_atom_meta(atom_type: str) -> AtomMeta | None:
    return ATOM_REGISTRY.get(atom_type)


def get_all_atoms() -> dict[str, AtomMeta]:
    return dict(ATOM_REGISTRY)


def get_whitelist() -> set[str]:
    return set(ATOM_REGISTRY.keys())


def get_high_risk_atoms() -> set[str]:
    return {k for k, v in ATOM_REGISTRY.items() if v.risk_level == 'high'}


def get_backup_required_atoms() -> set[str]:
    """需要前置备份的原子：dependencies 中包含 backup_file 的"""
    return {k for k, v in ATOM_REGISTRY.items() if 'backup_file' in v.dependencies}


def get_atoms_by_group(group: str) -> dict[str, AtomMeta]:
    return {k: v for k, v in ATOM_REGISTRY.items() if v.group == group}

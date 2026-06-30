# -*- coding: utf-8 -*-
"""Diff algorithms for identity sync — Dept tree diff and user list diff

Provides pure diff logic (no I/O) that compares remote entries against
local mapping snapshots to produce add/update/disable action lists.

Design decisions:
  - NEVER delete local records; only mark disabled (status=False / is_active=False)
  - Dept is matched by remote_dn (LDAP DN is the stable identifier)
  - User is matched by remote_dn; username is used as fallback for display
  - Parent dept chain is auto-created when a dept's parent DN is not mapped yet
"""

from dataclasses import dataclass, field
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


# ── Data structures ──────────────────────────────────────────────

@dataclass
class DeptNode:
    """A department node from the remote directory"""
    dn: str                         # LDAP Distinguished Name, e.g. "OU=IT,DC=example,DC=com"
    name: str                       # Department name, e.g. "IT Department"
    parent_dn: Optional[str] = None  # Parent DN inferred from DN hierarchy
    attributes: dict = field(default_factory=dict)  # Raw remote attributes


@dataclass
class UserEntry:
    """A user entry from the remote directory"""
    dn: str                # LDAP DN
    username: str          # Login name (e.g. sAMAccountName)
    dept_dn: Optional[str] = None  # Department DN
    attributes: dict = field(default_factory=dict)  # Raw remote attributes


@dataclass
class DeptDiff:
    """Diff result for departments"""
    added: List[dict] = field(default_factory=list)     # [{dn, name, parent_dn, attrs}]
    updated: List[dict] = field(default_factory=list)   # [{dn, dept_id, attrs}]
    disabled: List[int] = field(default_factory=list)    # [dept_id, ...] — remote deleted


@dataclass
class UserDiff:
    """Diff result for users"""
    added: List[dict] = field(default_factory=list)     # [{dn, username, dept_dn, attrs}]
    updated: List[dict] = field(default_factory=list)   # [{dn, user_id, attrs}]
    disabled: List[int] = field(default_factory=list)    # [user_id, ...] — remote deleted


# ── Differ ───────────────────────────────────────────────────────

class Differ:
    """Pure diff logic — no DB queries, no I/O

    Usage:
        dept_diff = Differ.diff_depts(remote_depts, local_mappings_dict)
        user_diff = Differ.diff_users(remote_users, local_mappings_dict, dept_mapping_dn_to_id)
    """

    @staticmethod
    def parse_parent_dn(dn: str) -> Optional[str]:
        """Extract parent DN from a DN string

        Example:
            "OU=IT,OU=Company,DC=example,DC=com" → "OU=Company,DC=example,DC=com"
            "CN=Users,DC=example,DC=com" → "DC=example,DC=com"
            "DC=example,DC=com" → None (root)
        """
        if not dn:
            return None
        parts = dn.split(",", 1)
        if len(parts) < 2:
            return None
        return parts[1]

    @staticmethod
    def _dept_name_from_dn(dn: str) -> str:
        """Extract the name (RDN value) from a DN"""
        if not dn:
            return "Unknown"
        # RDN is the first part before comma, value is after "="
        rdn = dn.split(",", 1)[0]
        if "=" in rdn:
            return rdn.split("=", 1)[1]
        return rdn

    @classmethod
    def diff_depts(cls, remote_nodes: List[DeptNode],
                   local_mappings: dict) -> DeptDiff:
        """Compare remote dept nodes against local mappings

        Args:
            remote_nodes: Departments fetched from LDAP/AD
            local_mappings: Dict of {remote_dn: DeptMapping} from DB

        Returns:
            DeptDiff with add/update/disable actions
        """
        diff = DeptDiff()

        remote_dns = {n.dn for n in remote_nodes}
        local_dns = set(local_mappings.keys())

        # --- Added: remote has, local doesn't ---
        for node in remote_nodes:
            if node.dn not in local_mappings:
                parent_dn = cls.parse_parent_dn(node.dn)
                diff.added.append({
                    "dn": node.dn,
                    "name": node.name or cls._dept_name_from_dn(node.dn),
                    "parent_dn": parent_dn,
                    "attributes": node.attributes,
                })

        # --- Disabled: local has, remote doesn't ---
        for dn in local_dns:
            if dn not in remote_dns:
                mapping = local_mappings[dn]
                diff.disabled.append(mapping.dept_id)

        # --- Updated: both have, check attributes ---
        for node in remote_nodes:
            mapping = local_mappings.get(node.dn)
            if mapping is None:
                continue
            # Compare attribute snapshot
            old_attrs = mapping.remote_attrs or {}
            if cls._attrs_changed(old_attrs, node.attributes):
                diff.updated.append({
                    "dn": node.dn,
                    "dept_id": mapping.dept_id,
                    "attributes": node.attributes,
                })

        return diff

    @classmethod
    def diff_users(cls, remote_users: List[UserEntry],
                   local_mappings: dict,
                   dept_dn_to_id: dict) -> UserDiff:
        """Compare remote users against local mappings

        Args:
            remote_users: Users fetched from LDAP/AD
            local_mappings: Dict of {remote_dn: UserMapping} from DB
            dept_dn_to_id: Dict of {remote_dn: local_dept_id} for parent resolution

        Returns:
            UserDiff with add/update/disable actions
        """
        diff = UserDiff()

        remote_dns = {u.dn for u in remote_users}
        local_dns = set(local_mappings.keys())

        # --- Added ---
        for user in remote_users:
            if user.dn not in local_mappings:
                dept_id = dept_dn_to_id.get(user.dept_dn) if user.dept_dn else None
                diff.added.append({
                    "dn": user.dn,
                    "username": user.username,
                    "dept_id": dept_id,
                    "attributes": user.attributes,
                })

        # --- Disabled ---
        for dn in local_dns:
            if dn not in remote_dns:
                mapping = local_mappings[dn]
                diff.disabled.append(mapping.user_id)

        # --- Updated ---
        for user in remote_users:
            mapping = local_mappings.get(user.dn)
            if mapping is None:
                continue
            old_attrs = mapping.remote_attrs or {}
            if cls._attrs_changed(old_attrs, user.attributes):
                dept_id = dept_dn_to_id.get(user.dept_dn) if user.dept_dn else None
                diff.updated.append({
                    "dn": user.dn,
                    "user_id": mapping.user_id,
                    "attributes": user.attributes,
                    "username": user.username,
                    "dept_id": dept_id,
                })

        return diff

    @staticmethod
    def _attrs_changed(old: dict, new: dict,
                       tracked_keys: Optional[List[str]] = None) -> bool:
        """Check if relevant remote attributes have changed

        Compares only string/numeric/int values — ignores binary fields.
        If tracked_keys is None, compares all keys present in 'new'.
        """
        keys = tracked_keys or new.keys()
        for key in keys:
            old_val = str(old.get(key, "")).strip()
            new_val = str(new.get(key, "")).strip()
            if old_val != new_val:
                logger.debug("Attr changed: %s '%s' → '%s'", key, old_val, new_val)
                return True
        return False

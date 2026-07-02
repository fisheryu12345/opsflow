# -*- coding: utf-8 -*-
"""Identity sync provider — orchestrate full sync from LDAP/AD to local Dept & Users

BaseSyncProvider is the abstract base; LDAPSyncProvider implements LDAP/AD sync
by consuming a ConnectorInstance's connection config and credentials.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict
import logging

from django.utils import timezone

from integration.models.connector import ConnectorInstance
from integration.adapters.auth.ldap import LDAPConnector

from iam.sync.models import DeptMapping, UserMapping
from iam.sync.differ import (
    Differ, DeptNode, UserEntry,
    DeptDiff, UserDiff,
)

logger = logging.getLogger(__name__)


@dataclass
class SyncStats:
    """Sync execution statistics"""
    dept_added: int = 0
    dept_updated: int = 0
    dept_disabled: int = 0
    user_added: int = 0
    user_updated: int = 0
    user_disabled: int = 0


@dataclass
class SyncResult:
    """Result of a sync run"""
    success: bool = True
    stats: SyncStats = field(default_factory=SyncStats)
    error: Optional[str] = None
    errors: list = field(default_factory=list)  # Individual item errors


class BaseSyncProvider(ABC):
    """Abstract base for identity sync providers

    Each provider subclass knows how to:
      - fetch remote dept tree and user list from its source
      - map remote attributes to local field values
    """

    def __init__(self, instance: ConnectorInstance):
        self.instance = instance
        self.config = instance.config or {}
        self.field_mapping = self.config.get("field_mapping", {})

    @abstractmethod
    def fetch_depts(self) -> List[DeptNode]:
        """Fetch department tree from remote source"""

    @abstractmethod
    def fetch_users(self, dept_dn_to_id: Dict[str, int]) -> List[UserEntry]:
        """Fetch users from remote source

        Args:
            dept_dn_to_id: Map from remote dept DN to local dept_id,
                           populated after dept sync phase.
        """

    def sync_full(self) -> SyncResult:
        """Run full sync: dept diff → apply dept → user diff → apply user

        Returns:
            SyncResult with stats and any errors.
        """
        result = SyncResult(stats=SyncStats())

        try:
            # Phase 1: Sync departments
            logger.info("[%s] Starting dept sync...", self.instance.name)
            remote_depts = self.fetch_depts()
            logger.info("[%s] Fetched %d remote depts", self.instance.name, len(remote_depts))

            dept_mappings = {
                m.remote_dn: m
                for m in DeptMapping.objects.filter(source_instance=self.instance)
                .select_related("dept")
            }
            dept_diff = Differ.diff_depts(remote_depts, dept_mappings)
            self._apply_dept_diff(dept_diff, result)

            # Build dept_dn → dept_id map for user sync
            updated_mappings = {
                m.remote_dn: m
                for m in DeptMapping.objects.filter(source_instance=self.instance)
                .select_related("dept")
            }
            dept_dn_to_id = {
                dn: m.dept_id for dn, m in updated_mappings.items()
            }

            # Phase 2: Sync users
            logger.info("[%s] Starting user sync...", self.instance.name)
            remote_users = self.fetch_users(dept_dn_to_id)
            logger.info("[%s] Fetched %d remote users", self.instance.name, len(remote_users))

            user_mappings = {
                m.remote_dn: m
                for m in UserMapping.objects.filter(source_instance=self.instance)
                .select_related("user")
            }
            user_diff = Differ.diff_users(remote_users, user_mappings, dept_dn_to_id)
            self._apply_user_diff(user_diff, result)

            logger.info("[%s] Sync complete: %s", self.instance.name, result.stats)

        except Exception as e:
            logger.exception("[%s] Sync failed: %s", self.instance.name, e)
            result.success = False
            result.error = str(e)

        return result

    def _apply_dept_diff(self, diff: DeptDiff, result: SyncResult):
        """Apply department diff to database"""
        from iam.models import IAMDept

        # --- Added ---
        for item in diff.added:
            try:
                # Resolve parent dept
                parent = None
                if item["parent_dn"]:
                    parent_mapping = DeptMapping.objects.filter(
                        source_instance=self.instance,
                        remote_dn=item["parent_dn"],
                    ).first()
                    if parent_mapping:
                        parent = parent_mapping.dept

                # Create Dept
                dept = IAMDept.objects.create(
                    name=item["name"],
                    key=item["dn"],  # Store DN as key for traceability
                    parent=parent,
                    status=True,
                )
                # Create mapping
                DeptMapping.objects.create(
                    source_instance=self.instance,
                    dept=dept,
                    remote_dn=item["dn"],
                    remote_attrs=item["attributes"],
                )
                result.stats.dept_added += 1
                logger.debug("Dept added: %s (%s)", dept.name, item["dn"])
            except Exception as e:
                logger.warning("Failed to add dept %s: %s", item["dn"], e)
                result.errors.append({"action": "dept_add", "dn": item["dn"], "error": str(e)})

        # --- Updated ---
        for item in diff.updated:
            try:
                mapping = DeptMapping.objects.filter(
                    source_instance=self.instance,
                    remote_dn=item["dn"],
                ).first()
                if mapping:
                    # Update Dept fields based on field_mapping
                    dept = mapping.dept
                    dirty = False
                    for local_field, remote_attr in self.field_mapping.items():
                        if local_field == "name" and remote_attr in item["attributes"]:
                            val = item["attributes"].get(remote_attr, "")
                            if val and dept.name != val:
                                dept.name = val
                                dirty = True
                    if dirty:
                        dept.save(update_fields=["name"])
                    # Update remote_attrs snapshot
                    mapping.remote_attrs = item["attributes"]
                    mapping.save(update_fields=["remote_attrs"])
                    result.stats.dept_updated += 1
            except Exception as e:
                logger.warning("Failed to update dept %s: %s", item["dn"], e)
                result.errors.append({"action": "dept_update", "dn": item["dn"], "error": str(e)})

        # --- Disabled ---
        for dept_id in diff.disabled:
            try:
                IAMDept.objects.filter(id=dept_id).update(status=False)
                result.stats.dept_disabled += 1
            except Exception as e:
                logger.warning("Failed to disable dept %d: %s", dept_id, e)

    def _apply_user_diff(self, diff: UserDiff, result: SyncResult):
        """Apply user diff to database"""
        from iam.models import IAMUsers

        # --- Added ---
        for item in diff.added:
            try:
                # Resolve dept
                dept_id = item.get("dept_id")
                dept = None
                if dept_id:
                    from iam.models import IAMDept
                    dept = IAMDept.objects.filter(id=dept_id).first()

                # Build user fields from mapping
                user_data = {
                    "username": item["username"],
                    "name": self._map_attr("name", item["attributes"], item["username"]),
                    "email": self._map_attr("email", item["attributes"], ""),
                    "mobile": self._map_attr("mobile", item["attributes"], ""),
                    "is_active": True,
                    "dept": dept,
                }
                # Set a default password (user will login via LDAP Bind)
                user = IAMUsers.objects.create(**user_data)

                UserMapping.objects.create(
                    source_instance=self.instance,
                    user=user,
                    remote_dn=item["dn"],
                    remote_attrs=item["attributes"],
                )
                result.stats.user_added += 1
                logger.debug("User added: %s (%s)", user.username, item["dn"])
            except Exception as e:
                logger.warning("Failed to add user %s: %s", item.get("username", "?"), e)
                result.errors.append({"action": "user_add", "dn": item["dn"], "error": str(e)})

        # --- Updated ---
        for item in diff.updated:
            try:
                mapping = UserMapping.objects.filter(
                    source_instance=self.instance,
                    remote_dn=item["dn"],
                ).select_related("user").first()
                if mapping:
                    user = mapping.user
                    dirty = False

                    # Update fields from mapping
                    name = self._map_attr("name", item["attributes"], user.username)
                    if name and user.name != name:
                        user.name = name
                        dirty = True
                    email = self._map_attr("email", item["attributes"], "")
                    if email and user.email != email:
                        user.email = email
                        dirty = True
                    mobile = self._map_attr("mobile", item["attributes"], "")
                    if mobile and user.mobile != mobile:
                        user.mobile = mobile
                        dirty = True

                    # Re-assign dept if changed
                    new_dept_id = item.get("dept_id")
                    if new_dept_id and (user.dept_id != new_dept_id):
                        user.dept_id = new_dept_id
                        dirty = True

                    if dirty:
                        user.save(update_fields=["name", "email", "mobile", "dept_id"])

                    mapping.remote_attrs = item["attributes"]
                    mapping.save(update_fields=["remote_attrs"])
                    result.stats.user_updated += 1
            except Exception as e:
                logger.warning("Failed to update user %s: %s", item.get("username", "?"), e)
                result.errors.append({"action": "user_update", "dn": item["dn"], "error": str(e)})

        # --- Disabled ---
        for user_id in diff.disabled:
            try:
                IAMUsers.objects.filter(id=user_id).update(is_active=False)
                result.stats.user_disabled += 1
            except Exception as e:
                logger.warning("Failed to disable user %d: %s", user_id, e)

    def _map_attr(self, local_field: str, attrs: dict, default="") -> str:
        """Map a local field name to a remote attribute value via field_mapping"""
        remote_attr = self.field_mapping.get(local_field)
        if remote_attr and remote_attr in attrs:
            val = attrs[remote_attr]
            return str(val) if val is not None else default
        return default


class LDAPSyncProvider(BaseSyncProvider):
    """Sync provider for LDAP/AD directories

    Reads connection config and credential from the ConnectorInstance,
    then uses LDAPConnector to search the directory.
    """

    def fetch_depts(self) -> List[DeptNode]:
        """Fetch department/OU tree from LDAP/AD"""
        connector = LDAPConnector(self.instance)
        search_filter = self.config.get(
            "dept_search_filter",
            "(objectClass=organizationalUnit)",
        )
        results = connector.search(search_filter, attributes=["ou", "name", "description"])

        nodes = []
        for entry in results:
            attrs = entry.get("attributes", {})
            dn = entry.get("dn", "")
            # If name not specified in attrs, extract from DN
            name = attrs.get("name") or attrs.get("ou") or Differ._dept_name_from_dn(dn)
            nodes.append(DeptNode(
                dn=dn,
                name=str(name),
                parent_dn=Differ.parse_parent_dn(dn),
                attributes=attrs,
            ))
        return nodes

    def fetch_users(self, dept_dn_to_id: Dict[str, int]) -> List[UserEntry]:
        """Fetch users from LDAP/AD"""
        connector = LDAPConnector(self.instance)
        search_filter = self.config.get(
            "user_search_filter",
            "(objectClass=person)",
        )
        # Collect the attributes we need based on field_mapping
        attrs_needed = set(self.field_mapping.values())
        attrs_needed.add(self.config.get("username_attr", "sAMAccountName"))
        # Also get department attribute for dept assignment
        attrs_needed.add("department")
        results = connector.search(search_filter, attributes=list(attrs_needed))

        username_attr = self.config.get("username_attr", "sAMAccountName")

        users = []
        for entry in results:
            attrs = entry.get("attributes", {})
            dn = entry.get("dn", "")
            username = str(attrs.get(username_attr, ""))
            if not username:
                continue  # Skip entries without a username

            # Resolve department DN from the user's department attribute
            dept_dn = None
            dept_attr = attrs.get("department")
            if dept_attr:
                # Try to find matching dept DN by name
                dept_name = str(dept_attr)
                for remote_dn, local_id in dept_dn_to_id.items():
                    if dept_name.lower() in remote_dn.lower():
                        dept_dn = remote_dn
                        break

            users.append(UserEntry(
                dn=dn,
                username=username,
                dept_dn=dept_dn,
                attributes=attrs,
            ))
        return users

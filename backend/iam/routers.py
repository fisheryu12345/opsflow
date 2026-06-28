"""Tenant database router — physical isolation extension point.

Current behavior: routes ALL models to the 'default' database.
When a Business.db_alias is set to a non-null value (e.g. 'tenant_acme'),
this router can route that business's queries to a separate database.

Implementation note: the router currently always returns None (no opinion)
for all operations. To enable physical isolation:
1. Add a separate database in settings.DATABASES (e.g. 'tenant_acme')
2. Set Business.db_alias = 'tenant_acme'
3. Uncomment and implement the routing logic below
"""


class TenantDatabaseRouter:
    """Routes database operations based on Business.db_alias.

    Currently a skeleton — all operations use 'default'.
    """

    def db_for_read(self, model, **hints):
        return 'default'

    def db_for_write(self, model, **hints):
        return 'default'

    def allow_relation(self, obj1, obj2, **hints):
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        return db == 'default'

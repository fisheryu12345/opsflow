#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import warnings


def main():
    """Run administrative tasks."""
    # 过滤 drf-spectacular 的 schema 生成警告（get_modifier_name/creator.name 等）
    warnings.filterwarnings("ignore", message=".*unable to resolve type hint.*")
    warnings.filterwarnings("ignore", message=".*could not resolve field on model.*")
    warnings.filterwarnings("ignore", message=".*unable to guess serializer.*")
    warnings.filterwarnings("ignore", message=".*unable to resolve authenticator.*")
    warnings.filterwarnings("ignore", message=".*consider adding a type to the path.*")
    warnings.filterwarnings("ignore", message=".*could not derive type.*")
    warnings.filterwarnings("ignore", message=".*enum naming encountered.*")
    warnings.filterwarnings("ignore", message=".*encountered multiple names.*")
    warnings.filterwarnings("ignore", message=".*operationId.*collisions.*")

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'application.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()

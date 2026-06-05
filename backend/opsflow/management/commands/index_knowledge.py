"""
Index all knowledge entries for vector search.
批量索引所有知识条目以供向量搜索。

Usage: python manage.py index_knowledge [--reset]
"""
import logging

from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Index all knowledge entries for vector search"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            dest="reset",
            help="Re-index all entries (clear existing embeddings)",
        )

    def handle(self, *args, **options):
        from opsflow.models import OpsKnowledge
        from opsflow.services.vector_service import VectorService

        reset = options.get("reset", False)

        if reset:
            # Clear all existing embeddings
            updated = OpsKnowledge.objects.exclude(embedding__isnull=True).update(embedding=None)
            self.stdout.write(f"Cleared {updated} existing embeddings")

        count = VectorService.index_all()
        if count == 0:
            self.stdout.write(self.style.WARNING("No new entries to index"))
        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully indexed {count} knowledge entries")
            )

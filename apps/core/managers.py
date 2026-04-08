from django.db import models
from django.utils import timezone


class SoftDeleteQuerySet(models.QuerySet):
    def ativos(self):
        return self.filter(deleted_at__isnull=True)

    def deletados(self):
        return self.filter(deleted_at__isnull=False)

    def delete(self):
        deleted_at = timezone.now()
        updated_count = self.ativos().update(deleted_at=deleted_at)
        return updated_count, {self.model._meta.label: updated_count}

    def hard_delete(self):
        return super().delete()

    def restore(self):
        restored_count = self.deletados().update(deleted_at=None)
        return restored_count


class ActiveManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().ativos()


class AllObjectsManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    pass

from django.db import models
from django.utils import timezone

from .managers import ActiveManager, AllObjectsManager


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteModel(TimeStampedModel):
    deleted_at = models.DateTimeField(blank=True, null=True)

    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def soft_delete(self, commit=True):
        if self.deleted_at:
            return self

        self.deleted_at = timezone.now()
        if commit:
            self.save(update_fields=["deleted_at", "updated_at"])
        return self

    def restore(self, commit=True):
        if self.deleted_at is None:
            return self

        self.deleted_at = None
        if commit:
            self.save(update_fields=["deleted_at", "updated_at"])
        return self

    def delete(self, using=None, keep_parents=False):
        self.soft_delete()

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)


class BaseModel(SoftDeleteModel):
    class Meta:
        abstract = True

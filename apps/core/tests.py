from django.db import connection, models
from django.test import TestCase, TransactionTestCase
from django.test.utils import isolate_apps
from django.urls import reverse

from apps.core.models import BaseModel
from apps.core.repositories import BaseRepository
from apps.core.services import BaseService


class CoreSmokeTests(TestCase):
    def test_home_redirects_to_licitacoes(self):
        response = self.client.get(reverse("home"))

        self.assertRedirects(response, reverse("licitacoes:index"))


@isolate_apps("apps.core")
class CoreFoundationTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        class DummyModel(BaseModel):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "core"
                ordering = ("id",)

        cls.DummyModel = DummyModel

        class DummyRepository(BaseRepository):
            model = DummyModel

        cls.DummyRepository = DummyRepository

        class DummyService(BaseService):
            repository_class = DummyRepository

        cls.DummyService = DummyService

        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(cls.DummyModel)

    @classmethod
    def tearDownClass(cls):
        try:
            with connection.schema_editor() as schema_editor:
                schema_editor.delete_model(cls.DummyModel)
        finally:
            super().tearDownClass()

    def test_active_manager_hides_soft_deleted_records(self):
        active = self.DummyModel.objects.create(name="Ativo")
        deleted = self.DummyModel.objects.create(name="Deletado")

        deleted.soft_delete()

        self.assertEqual(list(self.DummyModel.objects.values_list("name", flat=True)), ["Ativo"])
        self.assertEqual(
            list(self.DummyModel.all_objects.ativos().values_list("name", flat=True)),
            ["Ativo"],
        )
        self.assertEqual(
            list(self.DummyModel.all_objects.deletados().values_list("name", flat=True)),
            ["Deletado"],
        )
        self.assertEqual(active.deleted_at, None)

    def test_queryset_delete_and_restore_keep_record_available(self):
        instance = self.DummyModel.objects.create(name="Registro")

        deleted_count, deleted_map = self.DummyModel.all_objects.filter(pk=instance.pk).delete()

        self.assertEqual(deleted_count, 1)
        self.assertEqual(deleted_map, {self.DummyModel._meta.label: 1})
        self.assertFalse(self.DummyModel.objects.filter(pk=instance.pk).exists())

        restored_count = self.DummyModel.all_objects.deletados().restore()

        self.assertEqual(restored_count, 1)
        self.assertTrue(self.DummyModel.objects.filter(pk=instance.pk).exists())

    def test_repository_and_service_provide_simple_data_access(self):
        repository = self.DummyRepository()
        created = repository.create(name="Original")
        updated = repository.update(created, name="Atualizado")
        service = self.DummyService()

        self.assertEqual(updated.name, "Atualizado")
        self.assertTrue(repository.exists(name="Atualizado"))
        self.assertEqual(service.get_repository().__class__, self.DummyRepository)

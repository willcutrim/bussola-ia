from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    nome_completo = models.CharField(max_length=255, blank=True)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=30, blank=True)
    ativo = models.BooleanField(default=True)
    deve_trocar_senha = models.BooleanField(default=False)

    class Meta:
        ordering = ("username",)
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    def save(self, *args, **kwargs):
        self.is_active = self.ativo
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome_completo or self.username

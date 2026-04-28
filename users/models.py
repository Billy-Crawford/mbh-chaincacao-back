from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLES = [
        ('agriculteur',     'Agriculteur'),
        ('cooperative',     'Coopérative'),
        ('transformateur',  'Transformateur'),
        ('exportateur',     'Exportateur'),
        ('verificateur',    'Vérificateur'),
    ]

    role           = models.CharField(max_length=20, choices=ROLES)
    telephone      = models.CharField(max_length=20, blank=True)
    village        = models.CharField(max_length=100, blank=True)
    region         = models.CharField(max_length=100, blank=True)
    # wallet_address = models.CharField(max_length=42, blank=True)

    def __str__(self):
        return f"{self.username} ({self.role})"
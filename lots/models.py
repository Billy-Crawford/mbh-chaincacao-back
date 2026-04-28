import uuid
import hashlib
from django.db import models
from users.models import User


class Lot(models.Model):

    ESPECES = [
        ('forastero',  'Forastero'),
        ('trinitario', 'Trinitario'),
        ('criollo',    'Criollo'),
        ('arabica',    'Arabica'),
        ('robusta',    'Robusta'),
    ]

    STATUTS = [
        ('cree',       'Créé'),
        ('en_transit', 'En transit'),
        ('certifie',   'Certifié'),
        ('exporte',    'Exporté'),
    ]

    # ───────── IDENTIFIANT ─────────
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # ───────── RELATION ─────────
    agriculteur = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='lots'
    )

    # ───────── DONNÉES MÉTIER ─────────
    espece = models.CharField(max_length=20, choices=ESPECES)
    poids_kg = models.FloatField()
    gps_latitude = models.FloatField()
    gps_longitude = models.FloatField()
    date_recolte = models.DateField()
    photo = models.ImageField(upload_to='lots/', blank=True, null=True)
    notes = models.TextField(blank=True)
    statut = models.CharField(max_length=20, choices=STATUTS, default='cree')

    # ───────── BLOCKCHAIN ─────────
    tx_hash = models.CharField(max_length=100, blank=True)
    block_number = models.IntegerField(null=True, blank=True)

    blockchain_status = models.CharField(
        max_length=20,
        default="pending"
    )
    retry_count = models.IntegerField(default=0)

    # 🔥 hash du lot (audit / EUDR / anti-fake)
    data_hash = models.CharField(max_length=256, blank=True)

    # ───────── CLOUDINARY ─────────
    certificat_url = models.URLField(blank=True, null=True)
    qr_code_url = models.URLField(blank=True, null=True)

    # ───────── TIMESTAMP ─────────
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ───────── LOGIQUE HASH ─────────
    def calculer_hash(self):
        data = f"{self.id}{self.gps_latitude}{self.gps_longitude}{self.poids_kg}{self.date_recolte}{self.agriculteur_id}"
        return hashlib.sha256(data.encode()).hexdigest()

    def save(self, *args, **kwargs):
        # auto-save hash (optionnel mais propre)
        if not self.data_hash:
            self.data_hash = self.calculer_hash()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Lot {self.id} — {self.espece} {self.poids_kg}kg"
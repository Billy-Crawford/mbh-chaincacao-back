from django.db import models
from lots.models import Lot
from users.models import User


class Transfert(models.Model):
    ETAPES = [
        ('ferme_cooperative',           'Ferme → Coopérative'),
        ('cooperative_transformateur',  'Coopérative → Transformateur'),
        ('transformateur_exportateur',  'Transformateur → Exportateur'),
        ('exportateur_europe',          'Exportateur → Europe'),
    ]

    lot            = models.ForeignKey(Lot, on_delete=models.PROTECT, related_name='transferts')
    expediteur     = models.ForeignKey(User, on_delete=models.PROTECT, related_name='envois')
    destinataire   = models.ForeignKey(User, on_delete=models.PROTECT, related_name='receptions')
    etape          = models.CharField(max_length=40, choices=ETAPES)
    poids_verifie  = models.FloatField()
    notes          = models.TextField(blank=True)
    date_transfert = models.DateTimeField(auto_now_add=True)

    # Données blockchain
    tx_hash        = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"Transfert {self.lot.id} — {self.etape}"
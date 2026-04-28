from rest_framework import serializers
from .models import Transfert
from users.serializers import UserSerializer


class TransfertSerializer(serializers.ModelSerializer):
    expediteur_detail = UserSerializer(source='expediteur', read_only=True)
    destinataire_detail = UserSerializer(source='destinataire', read_only=True)

    class Meta:
        model = Transfert
        fields = [
            'id',
            'lot',
            'expediteur', 'expediteur_detail',
            'destinataire', 'destinataire_detail',
            'etape',
            'poids_verifie',
            'notes',
            'tx_hash',
            'date_transfert'
        ]

        read_only_fields = [
            'id',
            'expediteur',   # 🔥 OBLIGATOIRE
            'tx_hash',
            'date_transfert',
            'expediteur_detail',
            'destinataire_detail'
        ]
# transferts/serializers.py
from rest_framework import serializers
from .models import Transfert
from users.models import User
from users.serializers import UserSerializer


class TransfertSerializer(serializers.ModelSerializer):
    expediteur_detail = UserSerializer(source='expediteur', read_only=True)
    destinataire_detail = UserSerializer(source='destinataire', read_only=True)

    # 🔥 FIX CRITIQUE
    destinataire = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Transfert
        fields = [
            "id",
            "lot",
            "expediteur",
            "expediteur_detail",
            "destinataire",
            "destinataire_detail",
            "etape",
            "poids_verifie",
            "notes",
            "tx_hash",
            "date_transfert",
        ]

        read_only_fields = [
            "id",
            "expediteur",
            "tx_hash",
            "date_transfert",
            "expediteur_detail",
            "destinataire_detail",
        ]

    # 🔥 OPTIONNEL MAIS PROPRE (sécurise les données)
    def validate(self, data):
        etape = data.get("etape")

        # Si c'est une simple certification coop → destinataire facultatif
        if etape == "cooperative_transformateur":
            return data

        # Sinon on peut imposer un destinataire si nécessaire (future logique)
        return data


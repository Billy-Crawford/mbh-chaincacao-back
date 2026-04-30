# lots/serializers.py
from rest_framework import serializers
from .models import Lot
from users.serializers import UserSerializer


class LotSerializer(serializers.ModelSerializer):
    agriculteur_detail = UserSerializer(source='agriculteur', read_only=True)
    hash_donnees = serializers.SerializerMethodField()

    class Meta:
        model = Lot
        fields = [
            'id',
            'agriculteur',
            'agriculteur_detail',
            'espece',
            'poids_kg',
            'gps_latitude',
            'gps_longitude',
            'date_recolte',
            'photo',
            'notes',
            'statut',

            'tx_hash',
            'block_number',
            'blockchain_status',

            'qr_code_url',
            'certificat_url',

            'hash_donnees',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'agriculteur',
            'tx_hash',
            'block_number',
            'created_at',
            'updated_at'
        ]

    def get_hash_donnees(self, obj):
        return obj.calculer_hash()


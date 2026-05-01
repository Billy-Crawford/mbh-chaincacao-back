# lots/serializers.py

from rest_framework import serializers
from .models import Lot
from users.serializers import UserSerializer
from transferts.models import Transfert


class LotSerializer(serializers.ModelSerializer):
    agriculteur_detail = UserSerializer(source='agriculteur', read_only=True)

    poids_verifie = serializers.SerializerMethodField()
    date_reception = serializers.SerializerMethodField()
    historique = serializers.SerializerMethodField()
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
            'notes',
            'statut',

            'poids_verifie',
            'date_reception',
            'historique',

            'tx_hash',
            'blockchain_status',

            'qr_code_url',
            'certificat_url',

            'hash_donnees',
            'created_at',
        ]

    # =========================
    # DERNIER TRANSFERT
    # =========================
    def _last_transfer(self, obj):
        return Transfert.objects.filter(lot=obj).order_by("-date_transfert").first()

    def get_poids_verifie(self, obj):
        last = self._last_transfer(obj)
        return last.poids_verifie if last else obj.poids_kg

    def get_date_reception(self, obj):
        last = self._last_transfer(obj)
        return last.date_transfert if last else None

    # =========================
    # HISTORIQUE CLEAN (ANTI DOUBLON)
    # =========================
    def get_historique(self, obj):
        transferts = (
            Transfert.objects
            .filter(lot=obj)
            .order_by("date_transfert")
        )

        return [
            {
                "etape": t.etape,
                "date": t.date_transfert,
                "poids": t.poids_verifie,
                "tx_hash": t.tx_hash or "—",
            }
            for t in transferts
        ]

    def get_hash_donnees(self, obj):
        return obj.calculer_hash()





# class LotSerializer(serializers.ModelSerializer):
#     agriculteur_detail = UserSerializer(source='agriculteur', read_only=True)
#     hash_donnees = serializers.SerializerMethodField()
#
#     class Meta:
#         model = Lot
#         fields = [
#             'id',
#             'agriculteur',
#             'agriculteur_detail',
#             'espece',
#             'poids_kg',
#             'gps_latitude',
#             'gps_longitude',
#             'date_recolte',
#             'photo',
#             'notes',
#             'statut',
#
#             'tx_hash',
#             'block_number',
#             'blockchain_status',
#
#             'qr_code_url',
#             'certificat_url',
#
#             'hash_donnees',
#             'created_at',
#             'updated_at',
#         ]
#         read_only_fields = [
#             'id',
#             'agriculteur',
#             'tx_hash',
#             'block_number',
#             'created_at',
#             'updated_at'
#         ]
#
#     def get_hash_donnees(self, obj):
#         return obj.calculer_hash()


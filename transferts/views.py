# transferts/views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Transfert
from .serializers import TransfertSerializer
from lots.models import Lot
from blockchain.service import BlockchainService


# =========================
# ROLES AUTORISÉS PAR ÉTAPE
# =========================
ETAPE_ROLE = {
    'ferme_cooperative':          'agriculteur',   # ✅ FIX
    'cooperative_transformateur': 'cooperative',
    'transformateur_exportateur': 'transformateur',
}


class TransfertListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        transferts = Transfert.objects.filter(
            expediteur=request.user
        ).order_by('-date_transfert')

        return Response(TransfertSerializer(transferts, many=True).data)

    def post(self, request):
        etape = request.data.get('etape')
        lot_id = request.data.get('lot')

        try:
            lot = Lot.objects.get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({"error": "Lot introuvable"}, 404)

        # =========================
        # VALIDATION ETAPE
        # =========================
        role_requis = ETAPE_ROLE.get(etape)

        if not role_requis:
            return Response({"error": "Étape invalide"}, 400)

        if request.user.role != role_requis:
            return Response({
                "error": f"Seul {role_requis} peut effectuer cette action"
            }, 403)

        # =========================
        # ACCÈS COOP STRICT
        # =========================
        if request.user.role == 'cooperative':
            last_transfer = Transfert.objects.filter(
                lot=lot
            ).order_by('-date_transfert').first()

            if not last_transfer or last_transfer.destinataire != request.user:
                return Response({
                    "error": "Ce lot ne vous a pas été attribué"
                }, 403)

        # =========================
        # CREATION TRANSFERT
        # =========================
        serializer = TransfertSerializer(data=request.data)

        if serializer.is_valid():
            transfert = serializer.save(expediteur=request.user)

            blockchain = BlockchainService()
            tx_hash = blockchain.enregistrer_transfert(
                lot_id=str(lot.id),
                etape=etape,
                user_id=request.user.id
            )

            transfert.tx_hash = tx_hash or ""
            transfert.save()

            # =========================
            # UPDATE STATUT LOT
            # =========================
            lot.statut = 'en_transit'
            lot.save()

            return Response({
                "transfert": TransfertSerializer(transfert).data,
                "message": "Transfert validé"
            }, 201)

        return Response(serializer.errors, 400)


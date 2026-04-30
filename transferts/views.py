# transferts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Transfert
from .serializers import TransfertSerializer
from lots.models import Lot
from blockchain.service import BlockchainService


ETAPE_ROLE = {
    'ferme_cooperative': 'agriculteur',
    'cooperative_transformateur': 'cooperative',
    'transformateur_exportateur': 'transformateur',
}


class TransfertListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        etape = request.data.get("etape")
        lot_id = request.data.get("lot")

        try:
            lot = Lot.objects.get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({"error": "Lot introuvable"}, 404)

        role_requis = ETAPE_ROLE.get(etape)

        if not role_requis:
            return Response({"error": "Étape invalide"}, 400)

        if request.user.role != role_requis:
            return Response({"error": "Rôle invalide"}, 403)

        # =========================
        # COOP VALIDATION STRICTE
        # =========================
        if request.user.role == "cooperative":
            last = Transfert.objects.filter(lot=lot).order_by("-date_transfert").first()

            if not last or last.destinataire != request.user:
                return Response(
                    {"error": "Ce lot ne vous a pas été assigné"},
                    403
                )

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

            # ⚠️ IMPORTANT : NE PAS VALIDER LE LOT ICI
            lot.statut = "envoye"
            lot.save()

            return Response({
                "transfert": TransfertSerializer(transfert).data,
                "message": "Transfert enregistré"
            }, 201)

        return Response(serializer.errors, 400)

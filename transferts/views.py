# transferts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Transfert
from .serializers import TransfertSerializer
from lots.models import Lot
from blockchain.service import BlockchainService


ETAPE_ROLE = {
    "ferme_cooperative": "agriculteur",
    "cooperative_transformateur": "cooperative",
    "transformateur_exportateur": "transformateur",
}


ETAPE_DESTINATAIRE = {
    "ferme_cooperative": "cooperative",
    "cooperative_transformateur": "transformateur",
    "transformateur_exportateur": "exportateur",
}


class TransfertListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        etape = request.data.get("etape")
        lot_id = request.data.get("lot")
        poids = request.data.get("poids_verifie")
        notes = request.data.get("notes", "")

        # -------------------------
        # VALIDATION BASE
        # -------------------------
        try:
            lot = Lot.objects.get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({"error": "Lot introuvable"}, 404)

        if etape not in ETAPE_ROLE:
            return Response({"error": "Étape invalide"}, 400)

        if request.user.role != ETAPE_ROLE[etape]:
            return Response({"error": "Rôle non autorisé"}, 403)

        # -------------------------
        # DESTINATAIRE AUTO
        # -------------------------
        destinataire_role = ETAPE_DESTINATAIRE[etape]
        destinataire = None

        if etape == "ferme_cooperative":
            destinataire = None  # ou coop assignée si logique future
        else:
            from users.models import User
            destinataire = User.objects.filter(role=destinataire_role).first()

        # -------------------------
        # SERIALIZER SAFE
        # -------------------------
        serializer = TransfertSerializer(data={
            "lot": lot.id,
            "etape": etape,
            "poids_verifie": poids,
            "notes": notes,
            "destinataire": destinataire.id if destinataire else None,
        })

        if not serializer.is_valid():
            return Response({
                "error": "Données invalides",
                "details": serializer.errors
            }, 400)

        transfert = serializer.save(expediteur=request.user)

        # -------------------------
        # BLOCKCHAIN
        # -------------------------
        blockchain = BlockchainService()
        tx_hash = blockchain.enregistrer_transfert(
            lot_id=str(lot.id),
            etape=etape,
            user_id=request.user.id
        )

        transfert.tx_hash = tx_hash or ""
        transfert.save()

        return Response({
            "transfert": TransfertSerializer(transfert).data,
            "message": "Transfert enregistré avec succès"
        }, 201)




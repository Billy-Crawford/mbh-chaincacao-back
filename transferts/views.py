# transferts/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Transfert
from .serializers import TransfertSerializer
from lots.models import Lot
from users.models import User
from blockchain.service import BlockchainService


# =========================
# CONFIG METIER
# =========================
ETAPE_ROLE = {
    "ferme_cooperative": "agriculteur",
    "cooperative_transformateur": "cooperative",
    "transformateur_exportateur": "transformateur",
}

ETAPE_DESTINATAIRE_ROLE = {
    "ferme_cooperative": "cooperative",
    "cooperative_transformateur": "transformateur",
    "transformateur_exportateur": "exportateur",
}


class TransfertListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        etape = request.data.get("etape")
        lot_id = request.data.get("lot")

        try:
            lot = Lot.objects.get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({"error": "Lot introuvable"}, status=404)

        if etape not in ETAPE_ROLE:
            return Response({"error": "Étape invalide"}, status=400)

        role_requis = ETAPE_ROLE[etape]

        if request.user.role != role_requis:
            return Response({
                "error": "Rôle non autorisé",
                "required": role_requis,
                "your_role": request.user.role
            }, status=403)

        # =========================
        # ANTI-DOUBLON
        # =========================
        if Transfert.objects.filter(lot=lot, etape=etape).exists():
            return Response({
                "error": "Transfert déjà effectué pour cette étape"
            }, status=400)

        # =========================
        # VÉRIFICATION STATUT PRÉ-REQUIS
        # =========================
        STATUT_REQUIS = {
            "ferme_cooperative": "cree",
            "cooperative_transformateur": "receptionne",
            "transformateur_exportateur": "certifie",
        }

        statut_requis = STATUT_REQUIS.get(etape)
        if statut_requis and lot.statut != statut_requis:
            return Response({
                "error": f"Le lot doit être '{statut_requis}' avant cette étape. Statut actuel : '{lot.statut}'"
            }, status=400)

        # =========================
        # DESTINATAIRE — priorité au choix frontend
        # =========================
        destinataire_id = request.data.get("destinataire")
        destinataire_role = ETAPE_DESTINATAIRE_ROLE.get(etape)

        if destinataire_id:
            try:
                destinataire = User.objects.get(id=destinataire_id)
            except User.DoesNotExist:
                return Response({"error": "Transformateur introuvable"}, status=404)

            # Vérification du rôle du destinataire
            if destinataire.role != destinataire_role:
                return Response({
                    "error": f"Le destinataire doit avoir le rôle '{destinataire_role}'"
                }, status=400)
        else:
            # Fallback : premier utilisateur du bon rôle
            destinataire = User.objects.filter(role=destinataire_role).first()

        serializer = TransfertSerializer(data={
            "lot": lot.id,
            "etape": etape,
            "poids_verifie": request.data.get("poids_verifie"),
            "notes": request.data.get("notes", ""),
            "destinataire": destinataire.id if destinataire else None,
        })

        if not serializer.is_valid():
            return Response({
                "error": "Données invalides",
                "details": serializer.errors
            }, status=400)

        transfert = serializer.save(expediteur=request.user)

        # =========================
        # LOGIQUE STATUT LOT
        # =========================
        if etape == "ferme_cooperative":
            lot.statut = "en_transit"
        elif etape == "cooperative_transformateur":
            lot.statut = "receptionne"
        elif etape == "transformateur_exportateur":
            lot.statut = "certifie"

        lot.save()

        # =========================
        # BLOCKCHAIN SAFE
        # =========================
        try:
            blockchain = BlockchainService()
            tx_hash = blockchain.enregistrer_transfert(
                lot_id=str(lot.id),
                etape=etape,
                user_id=request.user.id
            )

            if tx_hash:
                transfert.tx_hash = tx_hash
                transfert.save()

        except Exception as e:
            print("BLOCKCHAIN ERROR:", e)

        return Response({
            "transfert": TransfertSerializer(transfert).data,
            "message": "Transfert OK"
        }, status=201)




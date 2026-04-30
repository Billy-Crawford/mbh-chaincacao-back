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

    # =========================
    # LISTE TRANSFERTS
    # =========================
    def get(self, request):
        transferts = Transfert.objects.filter(
            expediteur=request.user
        ).order_by('-date_transfert')

        return Response(TransfertSerializer(transferts, many=True).data)

    # =========================
    # ENVOI LOT
    # =========================
    def post(self, request):
        etape = request.data.get('etape')
        lot_id = request.data.get('lot')

        # 🔒 Vérification étape
        role_requis = ETAPE_ROLE.get(etape)
        if not role_requis:
            return Response(
                {'error': 'Étape invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 🔒 Vérification rôle
        if request.user.role != role_requis:
            return Response(
                {'error': f'Seul un {role_requis} peut effectuer cette action'},
                status=status.HTTP_403_FORBIDDEN
            )

        # 🔒 Récupération lot
        try:
            lot = Lot.objects.get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({'error': 'Lot introuvable'}, status=404)

        # =========================
        # 🔐 SÉCURITÉ MÉTIER
        # =========================

        # CAS AGRICULTEUR → doit posséder le lot
        if request.user.role == 'agriculteur':
            if lot.agriculteur != request.user:
                return Response(
                    {'error': "Ce lot ne vous appartient pas"},
                    status=status.HTTP_403_FORBIDDEN
                )

        # CAS AUTRES → doivent avoir reçu le lot
        else:
            autorise = Transfert.objects.filter(
                lot=lot,
                destinataire=request.user
            ).exists()

            if not autorise:
                return Response(
                    {'error': "Accès refusé à ce lot"},
                    status=status.HTTP_403_FORBIDDEN
                )

        # =========================
        # CRÉATION TRANSFERT
        # =========================
        serializer = TransfertSerializer(data=request.data)

        if serializer.is_valid():
            transfert = serializer.save(expediteur=request.user)

            # =========================
            # BLOCKCHAIN
            # =========================
            blockchain = BlockchainService()

            tx_hash = blockchain.enregistrer_transfert(
                lot_id=str(transfert.lot.id),
                etape=transfert.etape,
                user_id=request.user.id
            )

            if tx_hash:
                transfert.tx_hash = tx_hash
                transfert.save()

            # =========================
            # UPDATE LOT
            # =========================
            lot.statut = 'en_transit'
            lot.save()

            return Response({
                'transfert': TransfertSerializer(transfert).data,
                'message': '✅ Transfert enregistré'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



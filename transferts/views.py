from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Transfert
from .serializers import TransfertSerializer
from lots.models import Lot
from blockchain.service import BlockchainService
from users.permissions import EstAgriculteur, EstCooperative, EstTransformateur


# Mapping étape → rôle autorisé
ETAPE_ROLE = {
    'ferme_cooperative':          'agriculteur',
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
        etape = request.data.get('etape', '')

        # Vérifier que le rôle correspond à l'étape
        role_requis = ETAPE_ROLE.get(etape)
        if not role_requis:
            return Response(
                {'error': f'Étape invalide : {etape}'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if request.user.role != role_requis:
            return Response(
                {'error': f'Seul un {role_requis} peut effectuer l\'étape "{etape}"'},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = TransfertSerializer(data=request.data)
        if serializer.is_valid():
            transfert = serializer.save(expediteur=request.user)

            blockchain = BlockchainService()
            tx_hash = blockchain.enregistrer_transfert(
                lot_id  = str(transfert.lot.id),
                etape   = transfert.etape,
                user_id = request.user.id
            )
            if tx_hash:
                transfert.tx_hash = tx_hash
                transfert.save()

            lot = transfert.lot
            lot.statut = 'en_transit'
            lot.save()

            return Response({
                'transfert': TransfertSerializer(transfert).data,
                'message':   '✅ Transfert enregistré sur la blockchain !'
                             if tx_hash else '✅ Transfert créé (blockchain en attente)'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
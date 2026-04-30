# lots/views.py
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Lot
from .serializers import LotSerializer

from transferts.serializers import TransfertSerializer
from transferts.models import Transfert

from blockchain.service import BlockchainService
from users.permissions import EstAgriculteur, EstExportateur

import qrcode
import io
import cloudinary.uploader


# =========================
# LOT CREATE + LIST
# =========================

class LotListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.request.method == 'POST':
            return [EstAgriculteur()]
        return [IsAuthenticated()]

    def get(self, request):
        user = request.user

        # =========================
        # AGRICULTEUR
        # =========================
        if user.role == 'agriculteur':
            lots = Lot.objects.filter(
                agriculteur=user
            ).order_by('-created_at')

        # =========================
        # COOPERATIVE (🔥 CORRECTION ICI)
        # =========================
        elif user.role == 'cooperative':

            # ✅ UNIQUEMENT les lots envoyés à elle
            lots_ids = Transfert.objects.filter(
                destinataire=user
            ).values_list('lot_id', flat=True)

            lots = Lot.objects.filter(
                id__in=lots_ids
            ).order_by('-created_at')

        # =========================
        # EXPORTATEUR
        # =========================
        elif user.role == 'exportateur':
            lots = Lot.objects.filter(
                statut='en_transit'
            ).order_by('-created_at')

        else:
            lots = Lot.objects.none()

        return Response(LotSerializer(lots, many=True).data)

    def post(self, request):
        serializer = LotSerializer(data=request.data)

        if serializer.is_valid():
            lot = serializer.save(agriculteur=request.user)

            # =========================
            # BLOCKCHAIN
            # =========================
            blockchain = BlockchainService()
            tx_hash = blockchain.enregistrer_lot(
                lot_id=str(lot.id),
                hash_donnees=lot.calculer_hash()
            )

            lot.tx_hash = tx_hash if tx_hash else None
            lot.blockchain_status = "confirmed" if tx_hash else "pending"
            lot.save()

            # =========================
            # QR CODE
            # =========================
            verify_url = f"https://mbh-chaincacao-back.onrender.com/api/lots/{lot.id}/verify/"

            qr_url = generer_qr_code(
                verify_url,
                public_id=f"qr_lot_{lot.id}"
            )

            lot.qr_code_url = qr_url
            lot.save()

            return Response({
                'lot': LotSerializer(lot).data,
                'qr_code_url': qr_url,
                'tx_hash': tx_hash,
                'message': '✅ Lot créé'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =========================
# LOT DETAIL (sécurisé)
# =========================

class LotDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lot_id):
        try:
            lot = Lot.objects.get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({'error': 'Lot introuvable'}, status=404)

        user = request.user

        # 🔒 AGRICULTEUR
        if user.role == 'agriculteur' and lot.agriculteur != user:
            return Response({'error': 'Accès refusé'}, status=403)

        # 🔒 COOPERATIVE
        if user.role == 'cooperative':
            autorise = Transfert.objects.filter(
                lot=lot,
                destinataire=user
            ).exists()

            if not autorise:
                return Response({'error': 'Accès refusé'}, status=403)

        return Response(LotSerializer(lot).data)


# =========================
# VERIFICATION PUBLIQUE (QR)
# =========================

class VerifierLotView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, lot_id):
        try:
            lot = Lot.objects.prefetch_related('transferts').get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({'error': 'Lot introuvable'}, status=404)

        blockchain = BlockchainService()

        return Response({
            'lot': LotSerializer(lot).data,
            'transferts': TransfertSerializer(lot.transferts.all(), many=True).data,
            'blockchain': {
                'tx_hash': lot.tx_hash or 'Non enregistré',
                'enregistre_sur_bc': blockchain.lot_existe_blockchain(str(lot.id)),
                'historique': blockchain.get_historique(str(lot.id)),
            },
        })


# =========================
# QR CODE
# =========================

def generer_qr_code(url: str, public_id: str = None) -> str:
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(url)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    upload_result = cloudinary.uploader.upload(
        buffer,
        folder="qrcodes",
        public_id=public_id or f"qr_{url[-10:]}",
        resource_type="image"
    )

    return upload_result["secure_url"]

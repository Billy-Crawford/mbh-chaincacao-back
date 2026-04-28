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

    def get_permissions(self):
        if self.request.method == 'POST':
            return [EstAgriculteur()]
        return [IsAuthenticated()]

    def get(self, request):
        lots = Lot.objects.filter(agriculteur=request.user).order_by('-created_at')
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

            # if tx_hash:
            #     lot.tx_hash = tx_hash
            #     lot.save()

            if tx_hash:
                lot.tx_hash = tx_hash
                lot.blockchain_status = "confirmed"
            else:
                lot.blockchain_status = "pending"

            lot.save()

            # =========================
            # QR CODE LOT
            # =========================
            verify_url = f"http://localhost:8000/api/lots/{lot.id}/verify/"

            qr_url = generer_qr_code(
                verify_url,
                public_id=f"qr_lot_{lot.id}"
            )

            # IMPORTANT : champ correct
            if hasattr(lot, "qr_code_url"):
                lot.qr_code_url = qr_url
            else:
                lot.qr_code = qr_url

            lot.save()

            return Response({
                'lot': LotSerializer(lot).data,
                'qr_code_url': qr_url,
                'tx_hash': tx_hash,
                'message': '✅ Lot enregistré sur la blockchain !'
                if tx_hash else '✅ Lot créé (blockchain en attente)'
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =========================
# LOT DETAIL
# =========================

class LotDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lot_id):
        try:
            lot = Lot.objects.get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({'error': 'Lot introuvable'}, status=404)

        return Response(LotSerializer(lot).data)


# =========================
# VERIFICATION LOT
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
                'verification': '✅ Vérifié sur la blockchain'
                if blockchain.lot_existe_blockchain(str(lot.id)) else '⏳ En attente',
            },
            'eudr_conforme': bool(lot.tx_hash)
        })


# =========================
# EXPORT LOT
# =========================

class ExporterLotView(APIView):
    permission_classes = [EstExportateur]

    def post(self, request, lot_id):
        try:
            lot = Lot.objects.get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({'error': 'Lot introuvable'}, status=404)

        if lot.statut != 'en_transit':
            return Response({'error': 'Statut invalide'}, status=400)

        transfert = Transfert.objects.create(
            lot=lot,
            expediteur=request.user,
            destinataire=request.user,
            etape='exportateur_europe',
            poids_verifie=request.data.get('poids_verifie', lot.poids_kg),
            notes=request.data.get('notes', '')
        )

        blockchain = BlockchainService()
        tx_hash = blockchain.enregistrer_transfert(
            lot_id=str(lot.id),
            etape='exportateur_europe',
            user_id=request.user.id
        )

        if tx_hash:
            transfert.tx_hash = tx_hash
            transfert.save()

        lot.statut = 'exporte'
        lot.save()

        return Response({
            'transfert': TransfertSerializer(transfert).data,
            'lot': LotSerializer(lot).data,
            'certificat_eudr': f'http://localhost:8000/api/lots/{lot_id}/verify/',
            'message': '🚢 Lot exporté'
        })


# =========================
# QR CODE FUNCTION
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


# =========================
# SCANNER
# =========================

class ScannerLotView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lot_id):
        try:
            lot = Lot.objects.prefetch_related('transferts').get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({'error': 'Lot introuvable'}, status=404)

        etapes_faites = [t.etape for t in lot.transferts.all()]

        return Response({
            'lot': LotSerializer(lot).data,
            'historique_transferts': TransfertSerializer(lot.transferts.all(), many=True).data,
        })


# =========================
# CONFIRM RECEPTION
# =========================

class ConfirmerReceptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lot_id):
        try:
            lot = Lot.objects.get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({'error': 'Lot introuvable'}, status=404)

        transfert = Transfert.objects.create(
            lot=lot,
            expediteur=lot.agriculteur,
            destinataire=request.user,
            etape="reception",
            poids_verifie=request.data.get('poids_verifie', lot.poids_kg),
            notes=request.data.get('notes', '')
        )

        blockchain = BlockchainService()
        tx_hash = blockchain.enregistrer_transfert(
            lot_id=str(lot.id),
            etape="reception",
            user_id=request.user.id
        )

        if tx_hash:
            transfert.tx_hash = tx_hash
            transfert.save()

        return Response({
            'transfert': TransfertSerializer(transfert).data,
            'lot': LotSerializer(lot).data,
            'message': '✅ Réception confirmée'
        })


# =========================
# CERTIFICAT EUDR + CLOUDINARY
# =========================

class CertificatEUDRView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, lot_id):
        try:
            lot = Lot.objects.prefetch_related('transferts').get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({'error': 'Lot introuvable'}, status=404)

        blockchain = BlockchainService()

        blockchain_data = {
            'enregistre_sur_bc': blockchain.lot_existe_blockchain(str(lot.id)),
            'tx_hash': lot.tx_hash or '',
        }

        pdf_bytes = generer_certificat_eudr(
            lot,
            lot.transferts.all(),
            blockchain_data
        )

        file_obj = io.BytesIO(pdf_bytes)
        file_obj.seek(0)

        upload_result = cloudinary.uploader.upload(
            file_obj,
            resource_type="raw",
            folder="certificats_eudr",
            public_id=f"certificat_{lot.id}",
            format="pdf"
        )

        certificat_url = upload_result["secure_url"]

        qr_code = generer_qr_code(
            certificat_url,
            public_id=f"qr_certificat_{lot.id}"
        )

        if hasattr(lot, "certificat_url"):
            lot.certificat_url = certificat_url
            lot.qr_code_url = qr_code
            lot.save()

        return Response({
            "lot": LotSerializer(lot).data,
            "certificat_url": certificat_url,
            "qr_code": qr_code,
            "blockchain": blockchain_data,
            "message": "✅ Certificat généré"
        })
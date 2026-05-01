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

    def get(self, request):
        user = request.user

        if user.role == 'agriculteur':
            lots = Lot.objects.filter(agriculteur=user)


        elif user.role == 'cooperative':
            lots = Lot.objects.filter(
                transferts__destinataire=user
            ).exclude(statut="cree").distinct()

        # elif user.role == 'cooperative':
        #     # 🔥 IMPORTANT : uniquement assignés MAIS NON certifiés
        #     lots = Lot.objects.filter(
        #         transferts__destinataire=user,
        #         statut__in=["envoye", "en_attente_validation"]
        #     ).distinct()

        # elif user.role == 'cooperative':
        #     lots = Lot.objects.filter(
        #         transferts__destinataire=user
        #     ).distinct()

        elif user.role == 'transformateur':
            lots = Lot.objects.filter(
                transferts__destinataire=user
            ).distinct()


        elif user.role == 'exportateur':

            lots = Lot.objects.filter(

                transferts__destinataire=user,

                statut='certifie'

            ).distinct()

        else:
            lots = Lot.objects.none()

        return Response(LotSerializer(lots, many=True).data)

    def post(self, request):
        serializer = LotSerializer(data=request.data)

        if serializer.is_valid():
            lot = serializer.save(agriculteur=request.user)

            # ❌ IMPORTANT : PAS DE BLOCKCHAIN ICI
            lot.blockchain_status = "pending"
            lot.save()

            qr_url = generer_qr_code(
                f"https://mbh-chaincacao-back.onrender.com/api/lots/{lot.id}/verify/",
                public_id=f"qr_lot_{lot.id}"
            )

            lot.qr_code_url = qr_url
            lot.save()

            return Response({
                "lot": LotSerializer(lot).data,
                "qr_code_url": qr_url,
                "message": "Lot créé"
            }, 201)

        return Response(serializer.errors, 400)


# =========================
# LOT DETAIL
# =========================

class LotDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lot_id):
        try:
            lot = Lot.objects.get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({"error": "Lot introuvable"}, 404)

        user = request.user

        # =========================
        # AGRICULTEUR
        # =========================
        if user.role == 'agriculteur' and lot.agriculteur != user:
            return Response({"error": "Accès refusé"}, 403)

        # =========================
        # COOPERATIVE
        # =========================

        last_transfer = Transfert.objects.filter(lot=lot).order_by("-date_transfert").first()

        if not last_transfer or last_transfer.destinataire != user:
            return Response({"error": "Accès refusé"}, 403)

        # if user.role == 'cooperative':
        #     if not Transfert.objects.filter(
        #             lot=lot,
        #             destinataire=user
        #     ).exists():
        #         return Response({"error": "Accès refusé"}, 403)

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
            'certificat_eudr': f'https://mbh-chaincacao-back.onrender.com/api/lots/{lot_id}/verify/',
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

        # 🔥 CRITIQUE : UPDATE DU STATUT DU LOT
        lot.statut = "receptionne"
        lot.blockchain_status = "confirmed"
        lot.save()

        return Response({
            'transfert': TransfertSerializer(transfert).data,
            'lot': LotSerializer(lot).data,
            'message': 'Réception confirmée'
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


class CertifierLotView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, lot_id):
        try:
            lot = Lot.objects.get(id=lot_id)
        except Lot.DoesNotExist:
            return Response({"error": "Lot introuvable"}, 404)

        # =========================
        # VERIFICATION STRICTE
        # =========================
        if not Transfert.objects.filter(
            lot=lot,
            destinataire=request.user
        ).exists():
            return Response({"error": "Accès refusé"}, 403)

        poids = request.data.get("poids_verifie", lot.poids_kg)

        blockchain = BlockchainService()
        tx_hash = blockchain.enregistrer_transfert(
            lot_id=str(lot.id),
            etape="certification_cooperative",
            user_id=request.user.id
        )

        # =========================
        # FINAL STATE CORRECT
        # =========================
        lot.statut = "receptionne"   # 🔥 ICI LE VRAI MOMENT
        lot.blockchain_status = "confirmed"
        lot.tx_hash = tx_hash or ""
        lot.save()

        return Response({
            "message": "Lot certifié avec succès",
            "lot": LotSerializer(lot).data
        })



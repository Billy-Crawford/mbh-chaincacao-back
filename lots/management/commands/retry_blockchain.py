from django.core.management.base import BaseCommand
from lots.models import Lot
from blockchain.service import BlockchainService


class Command(BaseCommand):
    help = "Retry blockchain failed or pending transactions"

    def handle(self, *args, **kwargs):
        blockchain = BlockchainService()

        # 🔥 on prend pending + failed
        lots = Lot.objects.filter(blockchain_status__in=["pending", "failed"])

        self.stdout.write(f"🔄 Lots à traiter: {lots.count()}")

        for lot in lots:
            try:
                tx_hash = blockchain.enregistrer_lot(
                    lot_id=str(lot.id),
                    hash_donnees=lot.calculer_hash()
                )

                if tx_hash:
                    lot.tx_hash = tx_hash
                    lot.blockchain_status = "confirmed"
                    lot.save()

                    self.stdout.write(f"✔ Lot {lot.id} confirmé")

                else:
                    # blockchain service failed
                    lot.blockchain_status = "failed"
                    lot.save()

                    self.stdout.write(f"⚠ Lot {lot.id} échec blockchain")

            except Exception as e:
                lot.blockchain_status = "failed"
                lot.save()

                self.stdout.write(f"❌ Lot {lot.id} erreur: {str(e)}")
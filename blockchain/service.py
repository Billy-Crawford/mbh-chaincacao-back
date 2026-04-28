# from web3 import Web3

from web3 import Web3
from decouple import config
import json
import os


class BlockchainService:

    def __init__(self):
        self.w3 = Web3(Web3.HTTPProvider(config('BLOCKCHAIN_RPC_URL')))

        # 🔥 DEBUG IMPORTANT
        print("CONNECTED:", self.w3.is_connected())
        print("CHAIN ID:", self.w3.eth.chain_id)

        if not self.w3.is_connected():
            print("⚠️ Blockchain non connectée — mode dégradé")
            self.connected = False
            return

        self.connected = True

        abi_path = os.path.join(
            os.path.dirname(__file__), 'abi', 'ChainCacao.json'
        )

        with open(abi_path) as f:
            abi = json.load(f)

        # 🔥 FIX CRITIQUE : checksum address
        self.contract = self.w3.eth.contract(
            address=self.w3.to_checksum_address(config('CONTRACT_ADDRESS')),
            abi=abi
        )

        self.private_key = config('PRIVATE_KEY')
        self.account = self.w3.eth.account.from_key(self.private_key)

    def _build_and_send(self, fn) -> str:
        tx = fn.build_transaction({
            'from': self.account.address,
            'nonce': self.w3.eth.get_transaction_count(self.account.address),
            'gas': 150000,  # 🔥 un peu plus safe
            'gasPrice': self.w3.eth.gas_price,
            'chainId': config('CHAIN_ID', cast=int)  # 🔥 FIX IMPORTANT
        })

        signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
        tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

        return receipt.transactionHash.hex()

    def enregistrer_lot(self, lot_id: str, hash_donnees: str) -> str:
        # if not self.connected:
        #     return ""

        if not self.connected:
            raise Exception("Blockchain not connected")
        try:
            fn = self.contract.functions.creerLot(lot_id, hash_donnees)
            tx_hash = self._build_and_send(fn)
            print(f"✅ Lot enregistré sur blockchain : {tx_hash}")
            return tx_hash
        except Exception as e:
            print(f"❌ Erreur enregistrer_lot : {e}")
            return ""

        # except Exception as e:
        #     print(f"❌ Erreur enregistrer_lot : {e}")
        #     raise Exception(f"Blockchain failed: {str(e)}")

    def enregistrer_transfert(self, lot_id: str, etape: str, user_id: int) -> str:
        if not self.connected:
            return ""
        try:
            lot_id_clean = str(lot_id).strip()

            etape_complete = f"{etape}|user:{user_id}"

            print(f"📝 Transfert blockchain : lot='{lot_id_clean}' etape='{etape_complete}'")


            fn = self.contract.functions.transfererLot(
                lot_id,
                self.account.address,
                etape_complete
            )

            tx_hash = self._build_and_send(fn)
            print(f"✅ Transfert enregistré sur blockchain : {tx_hash}")
            return tx_hash

        except Exception as e:
            print(f"❌ Erreur enregistrer_transfert : {e}")
            return ""

    def get_historique(self, lot_id: str) -> list:
        if not self.connected:
            return []
        try:
            historique = self.contract.functions.getHistorique(lot_id).call()

            return [
                {
                    'expediteur': h[0],
                    'destinataire': h[1],
                    'etape': h[2],
                    'timestamp': h[3],
                }
                for h in historique
            ]

        except Exception as e:
            print(f"❌ Erreur get_historique : {e}")
            return []

    def lot_existe_blockchain(self, lot_id: str) -> bool:
        if not self.connected:
            return False
        try:
            return self.contract.functions.lotExiste(lot_id).call()
        except Exception as e:
            print(f"❌ Erreur lot_existe : {e}")
            return False










# from decouple import config
# import json
# import os
#
#
# class BlockchainService:
#
#     def __init__(self):
#         self.w3 = Web3(Web3.HTTPProvider(config('BLOCKCHAIN_RPC_URL')))
#
#         if not self.w3.is_connected():
#             print("⚠️ Blockchain non connectée — mode dégradé")
#             self.connected = False
#             return
#
#         self.connected = True
#
#         abi_path = os.path.join(
#             os.path.dirname(__file__), 'abi', 'ChainCacao.json'
#         )
#         with open(abi_path) as f:
#             abi = json.load(f)
#
#         self.contract = self.w3.eth.contract(
#             address = config('CONTRACT_ADDRESS'),
#             abi     = abi
#         )
#
#         # ✅ UN seul wallet — celui de l'application
#         self.private_key = config('PRIVATE_KEY')
#         self.account     = self.w3.eth.account.from_key(self.private_key)
#
#     def _build_and_send(self, fn) -> str:
#         """Méthode interne — construit, signe et envoie une transaction."""
#         tx = fn.build_transaction({
#             'from':     self.account.address,
#             'nonce':    self.w3.eth.get_transaction_count(self.account.address),
#             'gas':      200000,
#             'gasPrice': self.w3.eth.gas_price
#         })
#         signed  = self.w3.eth.account.sign_transaction(tx, self.private_key)
#         tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
#         receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
#         return receipt.transactionHash.hex()
#
#     def enregistrer_lot(self, lot_id: str, hash_donnees: str) -> str:
#         if not self.connected:
#             return ""
#         try:
#             fn = self.contract.functions.creerLot(lot_id, hash_donnees)
#             tx_hash = self._build_and_send(fn)
#             print(f"✅ Lot enregistré sur blockchain : {tx_hash}")
#             return tx_hash
#         except Exception as e:
#             print(f"❌ Erreur enregistrer_lot : {e}")
#             return ""
#
#     def enregistrer_transfert(self, lot_id: str, etape: str, user_id: int) -> str:
#         """
#         On n'utilise plus le wallet du destinataire.
#         On encode l'etape et le user_id dans la blockchain.
#         """
#         if not self.connected:
#             return ""
#         try:
#             # On passe l'adresse du wallet de l'app comme destinataire
#             # et on encode l'étape avec le user_id pour identifier l'acteur
#             etape_complete = f"{etape}|user:{user_id}"
#             fn = self.contract.functions.transfererLot(
#                 lot_id,
#                 self.account.address,   # ← toujours le wallet de l'app
#                 etape_complete
#             )
#             tx_hash = self._build_and_send(fn)
#             print(f"✅ Transfert enregistré sur blockchain : {tx_hash}")
#             return tx_hash
#         except Exception as e:
#             print(f"❌ Erreur enregistrer_transfert : {e}")
#             return ""
#
#     def get_historique(self, lot_id: str) -> list:
#         if not self.connected:
#             return []
#         try:
#             historique = self.contract.functions.getHistorique(lot_id).call()
#             return [
#                 {
#                     'expediteur':   h[0],
#                     'destinataire': h[1],
#                     'etape':        h[2],
#                     'timestamp':    h[3],
#                 }
#                 for h in historique
#             ]
#         except Exception as e:
#             print(f"❌ Erreur get_historique : {e}")
#             return []
#
#     def lot_existe_blockchain(self, lot_id: str) -> bool:
#         if not self.connected:
#             return False
#         try:
#             return self.contract.functions.lotExiste(lot_id).call()
#         except Exception as e:
#             print(f"❌ Erreur lot_existe : {e}")
#             return False
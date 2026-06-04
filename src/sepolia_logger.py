import os
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

RPC = os.getenv("SEPOLIA_RPC")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
ADDRESS = os.getenv("WALLET_ADDRESS")
CONTRACT_ADDRESS = os.getenv("CONTRACT_ADDRESS")

ABI = [
    {
        "inputs": [
            {"internalType": "string", "name": "_eventType", "type": "string"},
            {"internalType": "string", "name": "_message", "type": "string"}
        ],
        "name": "addEvent",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

class SepoliaLogger:

    def __init__(self):
        self.enabled = False

        try:
            if not RPC or not PRIVATE_KEY or not ADDRESS or not CONTRACT_ADDRESS:
                print("[SEPOLIA] Missing .env configuration")
                return

            self.w3 = Web3(Web3.HTTPProvider(RPC))

            self.contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(CONTRACT_ADDRESS),
                abi=ABI
            )

            self.enabled = True
            print("[SEPOLIA] Connected successfully")

        except Exception as e:
            print(f"[SEPOLIA ERROR] {e}")

    def log_event(self, event_type, message):

        if not self.enabled:
            return None

        try:
            nonce = self.w3.eth.get_transaction_count(ADDRESS)

            tx = self.contract.functions.addEvent(
                event_type,
                message
            ).build_transaction({
                "from": ADDRESS,
                "nonce": nonce,
                "gas": 300000,
                "gasPrice": self.w3.eth.gas_price,
                "chainId": 11155111
            })

            signed_tx = self.w3.eth.account.sign_transaction(
                tx,
                PRIVATE_KEY
            )

            tx_hash = self.w3.eth.send_raw_transaction(
                signed_tx.raw_transaction
            )

            tx_hex = tx_hash.hex()

            print(f"[SEPOLIA TX] {tx_hex}")

            return tx_hex

        except Exception as e:
            print(f"[SEPOLIA ERROR] {e}")
            return None

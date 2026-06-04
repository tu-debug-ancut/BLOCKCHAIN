"""
Blockchain Ledger - Lưu trữ bất biến các sự kiện mệt mỏi
Sử dụng Proof-of-Work đơn giản, lưu file JSON cục bộ
"""

import hashlib
import json
import time
import os
from datetime import datetime
from typing import List, Dict, Optional


class Block:
    """Một khối trong blockchain"""
    
    def __init__(self, index: int, data: dict, previous_hash: str, difficulty: int = 2):
        self.index = index
        self.timestamp = time.time()
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = 0
        self.difficulty = difficulty
        self.hash = self.mine_block()
    
    def compute_hash(self) -> str:
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine_block(self) -> str:
        """Proof-of-Work: tìm hash bắt đầu bằng '0' * difficulty"""
        prefix = "0" * self.difficulty
        while True:
            h = self.compute_hash()
            if h.startswith(prefix):
                return h
            self.nonce += 1
    
    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "datetime": datetime.fromtimestamp(self.timestamp).strftime("%Y-%m-%d %H:%M:%S"),
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
            "difficulty": self.difficulty
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "Block":
        block = cls.__new__(cls)
        block.index = d["index"]
        block.timestamp = d["timestamp"]
        block.data = d["data"]
        block.previous_hash = d["previous_hash"]
        block.nonce = d["nonce"]
        block.hash = d["hash"]
        block.difficulty = d.get("difficulty", 2)
        return block


class BlockchainLedger:
    """Blockchain cục bộ lưu sự kiện sức khỏe"""
    
    CHAIN_FILE = "fatigue_blockchain.json"
    DIFFICULTY = 2  # Tăng lên 3-4 để demo PoW thực sự
    
    EVENT_TYPES = {
        "BLINK_SLOW":    "Mắt nhắm chậm bất thường",
        "EYES_CLOSED":   "Mắt nhắm kéo dài (buồn ngủ)",
        "SEDENTARY":     "Ngồi yên quá lâu",
        "BREAK_TAKEN":   "Người dùng đã nghỉ giải lao",
        "SESSION_START": "Bắt đầu phiên làm việc",
        "SESSION_END":   "Kết thúc phiên làm việc",
        "POSTURE_BAD":   "Tư thế ngồi không tốt",
        "ALERT_SENT":    "Đã gửi cảnh báo"
    }
    
    def __init__(self):
        self.chain: List[Block] = []
        self._lock = __import__("threading").Lock()
        self._load_or_create()
    
    def _create_genesis(self):
        genesis_data = {
            "event": "SESSION_START",
            "message": "FatigueGuardian Blockchain khởi tạo",
            "version": "1.0.0",
            "node": "local"
        }
        genesis = Block(0, genesis_data, "0" * 64, self.DIFFICULTY)
        self.chain.append(genesis)
        self._save()
        print(f"[BLOCKCHAIN] Genesis block tạo thành công: {genesis.hash[:16]}...")
    
    def _load_or_create(self):
        if os.path.exists(self.CHAIN_FILE):
            try:
                with open(self.CHAIN_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.chain = [Block.from_dict(b) for b in data]
                if self._is_valid():
                    print(f"[BLOCKCHAIN] Đã tải {len(self.chain)} blocks từ file")
                    return
                else:
                    print("[BLOCKCHAIN] ⚠️  Chain bị hỏng, tạo lại...")
            except Exception as e:
                print(f"[BLOCKCHAIN] Lỗi đọc file: {e}, tạo mới...")
        self._create_genesis()
    
    def _save(self):
        with open(self.CHAIN_FILE, "w", encoding="utf-8") as f:
            json.dump([b.to_dict() for b in self.chain], f, ensure_ascii=False, indent=2)
    
    def _is_valid(self) -> bool:
        for i in range(1, len(self.chain)):
            curr = self.chain[i]
            prev = self.chain[i - 1]
            if curr.previous_hash != prev.hash:
                return False
        return True
    
    def add_event(self, event_type: str, details: dict = None) -> Block:
        """Thêm sự kiện sức khỏe vào blockchain"""
        with self._lock:
            data = {
                "event": event_type,
                "description": self.EVENT_TYPES.get(event_type, event_type),
                "details": details or {},
                "session_time": datetime.now().strftime("%H:%M:%S")
            }
            prev_hash = self.chain[-1].hash if self.chain else "0" * 64
            block = Block(len(self.chain), data, prev_hash, self.DIFFICULTY)
            self.chain.append(block)
            self._save()
            print(f"[BLOCKCHAIN] Block #{block.index} | {event_type} | Hash: {block.hash[:12]}... | Nonce: {block.nonce}")
            return block
    
    def get_recent_events(self, limit: int = 50) -> List[dict]:
        with self._lock:
            blocks = self.chain[-limit:][::-1]
            return [b.to_dict() for b in blocks]
    
    def get_stats(self) -> dict:
        with self._lock:
            total = len(self.chain)
            events_count = {}
            for block in self.chain:
                evt = block.data.get("event", "UNKNOWN")
                events_count[evt] = events_count.get(evt, 0) + 1
            
            today = datetime.now().strftime("%Y-%m-%d")
            today_blocks = [
                b for b in self.chain
                if datetime.fromtimestamp(b.timestamp).strftime("%Y-%m-%d") == today
            ]
            
            return {
                "total_blocks": total,
                "events_count": events_count,
                "today_events": len(today_blocks),
                "is_valid": self._is_valid(),
                "last_hash": self.chain[-1].hash if self.chain else "",
                "chain_integrity": "✅ Toàn vẹn" if self._is_valid() else "❌ Bị xâm phạm"
            }
    
    def get_chain_json(self) -> list:
        with self._lock:
            return [b.to_dict() for b in self.chain]

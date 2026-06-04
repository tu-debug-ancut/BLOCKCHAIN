# 🛡️ FatigueGuardian — Hệ thống nhắc nhở mệt mỏi văn phòng

## Tính năng chính

### 👁️ Nhận diện mắt (AI Camera)
- **Eye Aspect Ratio (EAR)**: Đo tỷ lệ mở/nhắm mắt bằng MediaPipe Face Mesh (468 điểm)
- Phát hiện **mắt nhắm ≥ 15 frame liên tiếp** → cảnh báo buồn ngủ
- Phát hiện **chớp mắt chậm** (EAR 0.21–0.23) → cảnh báo mỏi mắt
- Hiển thị EAR real-time, thanh trạng thái, threshold marker

### 🦵 Phát hiện ngồi yên
- So sánh pixel giữa các frame để detect chuyển động
- Ngồi yên > **30 phút** → thông báo "Dậy vận động!"
- Cooldown 5 phút giữa các cảnh báo cùng loại

### ⛓️ Blockchain (Proof-of-Work)
- Mỗi sự kiện sức khỏe được ghi vào **1 block**
- Block được **đào** bằng SHA-256 PoW (difficulty: 2 số 0 đầu)
- Chain liên kết bằng **previous_hash** → bất biến, không thể sửa
- Lưu local tại `fatigue_blockchain.json`
- Dashboard **Blockchain Explorer** xem từng block, hash, nonce

### 🔔 Thông báo
- Windows: Toast notification (win10toast / plyer)
- Âm thanh cảnh báo theo mức độ (critical/normal/low)
- Cooldown 5 phút tránh spam

### 📊 Dashboard Web (http://127.0.0.1:5050)
- Real-time EAR gauge + status
- Sedentary ring chart
- Blockchain event feed
- Full chain explorer với accordion blocks
- Nút "Ghi nhận nghỉ" để log break vào chain

---

## Cài đặt & Chạy

### Yêu cầu
- Python 3.9+ (https://python.org/downloads) — tick "Add to PATH"
- Webcam (nếu không có camera, hệ thống chạy Demo Mode)

### Cách chạy (Windows)
```
Double-click: RUN_WINDOWS.bat
```

### Cách chạy (thủ công)
```bash
pip install -r requirements.txt
python main.py
```

---

## Cấu trúc dự án
```
fatigue_guardian/
├── main.py                   ← Điểm khởi động
├── RUN_WINDOWS.bat           ← Launcher 1-click
├── requirements.txt
├── fatigue_blockchain.json   ← Dữ liệu blockchain (tự tạo)
├── src/
│   ├── detector.py           ← AI camera (MediaPipe EAR + Motion)
│   ├── blockchain_ledger.py  ← Blockchain engine (SHA-256 PoW)
│   ├── notifier.py           ← Hệ thống thông báo
│   └── web_dashboard.py      ← Flask API + SSE
└── templates/
    └── dashboard.html        ← Dashboard UI (HTML+JS+CSS)
```

---

## Ứng dụng Blockchain

| Tính năng | Chi tiết |
|-----------|---------|
| Algorithm | SHA-256 |
| Consensus | Proof-of-Work (difficulty 2) |
| Immutability | Hash-linked blocks |
| Integrity check | previous_hash verification |
| Storage | Local JSON (mở rộng được lên cloud) |

**Các loại event được ghi vào chain:**
- `SESSION_START/END` — Bắt/kết thúc phiên
- `EYES_CLOSED` — Phát hiện buồn ngủ
- `BLINK_SLOW` — Chớp mắt chậm
- `SEDENTARY` — Ngồi yên quá lâu
- `BREAK_TAKEN` — Đã nghỉ giải lao
- `ALERT_SENT` — Đã gửi thông báo

---

## Phím tắt (Cửa sổ Camera)
| Phím | Chức năng |
|------|----------|
| `q` | Thoát ứng dụng |
| `r` | Reset bộ đếm + ghi nhận nghỉ |

---

## Lưu ý
- Đảm bảo **đủ ánh sáng** để camera nhận diện mặt tốt
- Nhìn thẳng vào camera, không che mặt
- Nếu không có camera → hệ thống tự chạy **Demo Mode**

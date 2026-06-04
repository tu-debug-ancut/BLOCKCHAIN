"""
FatigueGuardian - Hệ thống nhắc nhở mệt mỏi cho văn phòng
Tích hợp: Camera AI + Blockchain + Dashboard Web
"""

import threading
import time
import sys
import os

def check_dependencies():
    """Kiểm tra và cài đặt dependencies"""
    missing = []
    
    try:
        import cv2
    except ImportError:
        missing.append("opencv-python")
    
    try:
        import mediapipe
    except ImportError:
        missing.append("mediapipe")
    
    try:
        import flask
    except ImportError:
        missing.append("flask")
    
    try:
        import numpy
    except ImportError:
        missing.append("numpy")
    
    try:
        import plyer
    except ImportError:
        missing.append("plyer")
    
    try:
        import pygame
    except ImportError:
        missing.append("pygame")
    
    if missing:
        print(f"[SETUP] Đang cài đặt: {', '.join(missing)}")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing + ["--quiet"])
        print("[SETUP] Cài đặt hoàn tất!\n")


if __name__ == "__main__":
    print("=" * 60)
    print("  🛡️  FATIGUE GUARDIAN - Hệ thống bảo vệ sức khỏe văn phòng")
    print("=" * 60)
    print("[INIT] Đang kiểm tra dependencies...")
    check_dependencies()
    
    # Import sau khi đã cài xong
    from src.detector import FatigueDetector
    from src.blockchain_ledger import BlockchainLedger
    from src.web_dashboard import create_app
    from src.notifier import Notifier
    
    print("[INIT] Khởi động Blockchain Ledger...")
    ledger = BlockchainLedger()
    
    print("[INIT] Khởi động hệ thống thông báo...")
    notifier = Notifier()
    
    print("[INIT] Khởi động Dashboard Web...")
    app = create_app(ledger)
    
    web_thread = threading.Thread(
        target=lambda: app.run(host="127.0.0.1", port=5050, debug=False, use_reloader=False),
        daemon=True
    )
    web_thread.start()
    
    print("[INIT] Khởi động Camera AI Detector...")
    detector = FatigueDetector(ledger=ledger, notifier=notifier)
    
    print("\n✅ Hệ thống sẵn sàng!")
    print("📊 Dashboard: http://127.0.0.1:5050")
    print("📷 Camera đang theo dõi...")
    print("⌨️  Nhấn 'q' để thoát\n")
    
    # Mở browser tự động
    import webbrowser
    threading.Timer(2.0, lambda: webbrowser.open("http://127.0.0.1:5050")).start()
    
    detector.run()

"""
FatigueDetector - Nhận diện mệt mỏi qua camera
- Eye Aspect Ratio (EAR): phát hiện mắt nhắm lâu
- Motion detection: phát hiện ngồi yên quá lâu
- MediaPipe Face Mesh + Pose
"""

import cv2
import numpy as np
import time
import threading
from datetime import datetime
from src.sepolia_logger import SepoliaLogger

try:
    import mediapipe as mp
    MEDIAPIPE_OK = True
except ImportError:
    MEDIAPIPE_OK = False


# ─── Chỉ số landmark mắt (MediaPipe 468-point mesh) ───
# Left eye: 33, 160, 158, 133, 153, 144
# Right eye: 362, 385, 387, 263, 373, 380
LEFT_EYE  = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# Toàn bộ face landmarks dùng để detect motion
FACE_OVAL = [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
             397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
             172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109]


class FatigueDetector:
    
    # ── Cấu hình ngưỡng ──────────────────────────────────
    EAR_THRESHOLD       = 0.21   # Dưới ngưỡng này = mắt nhắm
    EAR_CONSEC_FRAMES   = 15     # Số frame liên tiếp = cảnh báo ngủ gật
    SLOW_BLINK_EAR      = 0.23   # Ngưỡng chớp mắt chậm
    SLOW_BLINK_FRAMES   = 8      # Frame cho chớp chậm
    
    SEDENTARY_SECONDS   = 1800   # 30 phút ngồi yên = cảnh báo
    MOTION_THRESHOLD    = 18     # Pixel diff để nhận biết chuyển động
    
    ALERT_COOLDOWN      = 300    # 5 phút giữa 2 cảnh báo cùng loại
    
    def __init__(self, ledger, notifier):
        self.ledger   = ledger
        self.notifier = notifier
        self.sepolia = SepoliaLogger()
        
        # Trạng thái mắt
        self.ear_counter       = 0
        self.slow_blink_count  = 0
        self.total_blinks      = 0
        self.drowsy_alerts     = 0
        
        # Trạng thái chuyển động
        self.last_motion_time   = time.time()
        self.sedentary_alerted  = False
        self.prev_gray          = None
        self.motion_history     = []  # list of bool (30s window)
        
        # Cooldown alerts
        self.last_alert_time = {}
        
        # Thống kê live
        self.current_ear     = 1.0
        self.status_text     = "Đang theo dõi..."
        self.session_start   = time.time()
        self.frame_count     = 0
        
        # Shared state cho dashboard
        self.live_stats = {
            "ear": 1.0,
            "blinks": 0,
            "drowsy_alerts": 0,
            "sedentary_min": 0,
            "status": "OK",
            "motion": True
        }
        self._stats_lock = threading.Lock()
        
        # MediaPipe init
        if MEDIAPIPE_OK:
            self.mp_face = mp.solutions.face_mesh
            self.face_mesh = self.mp_face.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.5
            )
            self.mp_draw = mp.solutions.drawing_utils
            self.mp_styles = mp.solutions.drawing_styles
        else:
            print("[DETECTOR] ⚠️  MediaPipe không khả dụng, dùng Haar Cascade")
            self._init_haar()
    
    def _init_haar(self):
        """Fallback: dùng Haar Cascade nếu MediaPipe lỗi"""
        cc = cv2.data.haarcascades
        self.face_cascade = cv2.CascadeClassifier(cc + "haarcascade_frontalface_default.xml")
        self.eye_cascade  = cv2.CascadeClassifier(cc + "haarcascade_eye.xml")
    
    # ── EAR Calculation ─────────────────────────────────
    def _eye_aspect_ratio(self, landmarks, eye_indices, w, h) -> float:
        pts = []
        for idx in eye_indices:
            lm = landmarks[idx]
            pts.append(np.array([lm.x * w, lm.y * h]))
        
        # EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
        A = np.linalg.norm(pts[1] - pts[5])
        B = np.linalg.norm(pts[2] - pts[4])
        C = np.linalg.norm(pts[0] - pts[3])
        ear = (A + B) / (2.0 * C + 1e-6)
        return ear
    
    # ── Motion Detection ─────────────────────────────────
    def _detect_motion(self, gray_frame) -> bool:
        if self.prev_gray is None:
            self.prev_gray = gray_frame
            return True
        
        diff  = cv2.absdiff(self.prev_gray, gray_frame)
        _, th = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)
        motion_pixels = np.sum(th > 0)
        self.prev_gray = gray_frame
        
        # Tỉ lệ pixel thay đổi
        total_pixels = gray_frame.shape[0] * gray_frame.shape[1]
        motion_ratio = motion_pixels / total_pixels * 100
        return motion_ratio > 0.3  # > 0.3% frame thay đổi = có chuyển động
    
    # ── Alert system ─────────────────────────────────────
    def _can_alert(self, alert_type: str) -> bool:
        now = time.time()
        last = self.last_alert_time.get(alert_type, 0)
        if now - last > self.ALERT_COOLDOWN:
            self.last_alert_time[alert_type] = now
            return True
        return False
    
    def _trigger_drowsy_alert(self, ear: float):
        if not self._can_alert("DROWSY"):
            return
        self.drowsy_alerts += 1
        msg = f"⚠️ Phát hiện buồn ngủ! EAR={ear:.3f}"
        self.notifier.send(
            title="😴 Cảnh báo buồn ngủ!",
            message="Mắt bạn nhắm quá lâu. Hãy uống nước, nhìn xa, hoặc nghỉ 5 phút!",
            urgency="critical"
        )
        self.ledger.add_event("EYES_CLOSED", {
            "ear": round(ear, 4),
            "threshold": self.EAR_THRESHOLD,
            "frames": self.ear_counter
        })
        self.sepolia.log_event("EYES_CLOSED", "Phat hien buon ngu")
        self.status_text = "⚠️ BUỒN NGỦ PHÁT HIỆN!"
    
    def _trigger_sedentary_alert(self, minutes: float):
        if not self._can_alert("SEDENTARY"):
            return
        self.notifier.send(
            title="🦵 Dậy vận động đi!",
            message=f"Bạn đã ngồi yên {minutes:.0f} phút. Hãy đứng dậy, đi lại, vươn vai!",
            urgency="normal"
        )
        self.ledger.add_event("SEDENTARY", {
            "minutes_sedentary": round(minutes, 1),
            "threshold_minutes": self.SEDENTARY_SECONDS / 60
        })
        self.sepolia.log_event("SEDENTARY", f"Ngoi yen {minutes:.0f} phut")
        self.status_text = f"🦵 Ngồi yên {minutes:.0f} phút!"
    
    def _trigger_slow_blink(self, ear: float):
        if not self._can_alert("SLOW_BLINK"):
            return
        self.notifier.send(
            title="👁️ Mắt mệt mỏi",
            message="Chớp mắt chậm — dấu hiệu mỏi mắt. Nhìn vào điểm xa 20 giây.",
            urgency="low"
        )
        self.ledger.add_event("BLINK_SLOW", {"ear": round(ear, 4)})
    
    # ── Frame processing ──────────────────────────────────
    def _process_mediapipe(self, frame, gray):
        h, w = frame.shape[:2]
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        
        face_detected = False
        ear = 1.0
        
        if results.multi_face_landmarks:
            face_detected = True
            lms = results.multi_face_landmarks[0].landmark
            
            ear_l = self._eye_aspect_ratio(lms, LEFT_EYE,  w, h)
            ear_r = self._eye_aspect_ratio(lms, RIGHT_EYE, w, h)
            ear   = (ear_l + ear_r) / 2.0
            self.current_ear = ear
            
            # Vẽ mesh mắt
            for idx in LEFT_EYE + RIGHT_EYE:
                lm = lms[idx]
                px, py = int(lm.x * w), int(lm.y * h)
                cv2.circle(frame, (px, py), 2, (0, 255, 180), -1)
            
            # ── Logic mắt nhắm ──
            if ear < self.EAR_THRESHOLD:
                self.ear_counter += 1
                if self.ear_counter >= self.EAR_CONSEC_FRAMES:
                    self._trigger_drowsy_alert(ear)
                    self.status_text = "😴 BUỒN NGỦ!"
            else:
                if self.ear_counter > 0:
                    self.total_blinks += 1
                if self.EAR_THRESHOLD <= ear < self.SLOW_BLINK_EAR and self.ear_counter >= self.SLOW_BLINK_FRAMES:
                    self.slow_blink_count += 1
                    if self.slow_blink_count % 5 == 0:
                        self._trigger_slow_blink(ear)
                self.ear_counter = 0
                if "BUỒN NGỦ" not in self.status_text:
                    self.status_text = "✅ Bình thường"
        
        # ── Motion detection ──
        has_motion = self._detect_motion(gray)
        if has_motion or face_detected:
            self.last_motion_time = time.time()
            self.sedentary_alerted = False
        
        sedentary_sec = time.time() - self.last_motion_time
        sedentary_min = sedentary_sec / 60
        
        if sedentary_sec > self.SEDENTARY_SECONDS:
            self._trigger_sedentary_alert(sedentary_min)
        
        # ── Update live stats ──
        with self._stats_lock:
            self.live_stats.update({
                "ear": round(ear, 3),
                "blinks": self.total_blinks,
                "drowsy_alerts": self.drowsy_alerts,
                "sedentary_min": round(sedentary_min, 1),
                "status": "DROWSY" if ear < self.EAR_THRESHOLD else "OK",
                "motion": has_motion,
                "face_detected": face_detected,
                "session_min": round((time.time() - self.session_start) / 60, 1)
            })
        
        return frame, ear, sedentary_min, face_detected
    
    # ── Draw HUD ──────────────────────────────────────────
    def _draw_hud(self, frame, ear, sedentary_min, face_detected):
        h, w = frame.shape[:2]
        overlay = frame.copy()
        
        # Panel nền
        cv2.rectangle(overlay, (0, 0), (340, 200), (15, 15, 30), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)
        
        # Tiêu đề
        cv2.putText(frame, "FATIGUE GUARDIAN", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 220, 255), 2)
        
        # EAR
        ear_color = (0, 255, 100) if ear > self.EAR_THRESHOLD else (0, 60, 255)
        cv2.putText(frame, f"EAR: {ear:.3f}", (10, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, ear_color, 2)
        
        # Blink bar
        bar_w = int(min(ear / 0.4, 1.0) * 200)
        cv2.rectangle(frame, (90, 45), (290, 60), (50, 50, 50), -1)
        cv2.rectangle(frame, (90, 45), (90 + bar_w, 60), ear_color, -1)
        
        # Status
        status_col = (100, 255, 100) if "Bình thường" in self.status_text else (0, 80, 255)
        cv2.putText(frame, self.status_text[:30], (10, 90),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, status_col, 2)
        
        # Blinks & Alerts
        cv2.putText(frame, f"Chop mat: {self.total_blinks}  Canh bao: {self.drowsy_alerts}",
                    (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        
        # Sedentary
        sed_col = (0, 255, 180) if sedentary_min < 25 else (0, 100, 255)
        cv2.putText(frame, f"Ngoi yen: {sedentary_min:.1f} phut / {self.SEDENTARY_SECONDS//60}",
                    (10, 148), cv2.FONT_HERSHEY_SIMPLEX, 0.5, sed_col, 1)
        
        # Session time
        sess = (time.time() - self.session_start) / 60
        cv2.putText(frame, f"Phien: {sess:.0f} phut  |  Blockchain ON",
                    (10, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (150, 150, 255), 1)
        
        # Face detection dot
        dot_col = (0, 255, 0) if face_detected else (0, 0, 200)
        cv2.circle(frame, (320, 15), 8, dot_col, -1)
        cv2.putText(frame, "FACE", (295, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.35, dot_col, 1)
        
        # EAR threshold line indicator
        thresh_x = int(self.EAR_THRESHOLD / 0.4 * 200) + 90
        cv2.line(frame, (thresh_x, 43), (thresh_x, 62), (0, 165, 255), 2)
        
        return frame
    
    # ── Main loop ─────────────────────────────────────────
    def run(self):
        cap = cv2.VideoCapture(0)
        
        if not cap.isOpened():
            print("[DETECTOR] ❌ Không mở được camera! Demo mode...")
            self._run_demo_mode()
            return
        
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        cap.set(cv2.CAP_PROP_FPS, 30)
        
        self.ledger.add_event("SESSION_START", {
            "camera": "Webcam 0",
            "resolution": "640x480",
            "mediapipe": MEDIAPIPE_OK
        })
        
        print("[DETECTOR] Camera đang chạy. Nhấn 'q' để thoát, 'r' để reset.")
        
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                self.frame_count += 1
                frame = cv2.flip(frame, 1)
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                
                if MEDIAPIPE_OK:
                    frame, ear, sed_min, face_ok = self._process_mediapipe(frame, gray)
                else:
                    ear, sed_min, face_ok = 1.0, 0.0, False
                
                frame = self._draw_hud(frame, ear, sed_min, face_ok)
                
                cv2.imshow("FatigueGuardian | Nhan 'q' de thoat", frame)
                
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
                elif key == ord('r'):
                    self.total_blinks = 0
                    self.drowsy_alerts = 0
                    self.last_motion_time = time.time()
                    self.ledger.add_event("BREAK_TAKEN", {"reset_by": "user"})
                    print("[DETECTOR] Reset bộ đếm!")
        
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.ledger.add_event("SESSION_END", {
                "duration_min": round((time.time() - self.session_start) / 60, 1),
                "total_blinks": self.total_blinks,
                "drowsy_alerts": self.drowsy_alerts
            })
            print("[DETECTOR] Camera đã tắt.")
    
    def _run_demo_mode(self):
        """Chạy demo không cần camera - sinh dữ liệu giả"""
        import random
        print("[DETECTOR] 🎭 DEMO MODE: Sinh dữ liệu mô phỏng...")
        
        events = [
            ("EYES_CLOSED", {"ear": 0.15, "frames": 20}),
            ("BLINK_SLOW",  {"ear": 0.22}),
            ("SEDENTARY",   {"minutes_sedentary": 32}),
            ("BREAK_TAKEN", {"reason": "demo"}),
        ]
        
        for i, (evt, details) in enumerate(events * 3):
            time.sleep(3)
            self.ledger.add_event(evt, details)
            self.total_blinks += random.randint(1, 5)
            ear = round(random.uniform(0.1, 0.35), 3)
            with self._stats_lock:
                self.live_stats.update({
                    "ear": ear,
                    "blinks": self.total_blinks,
                    "drowsy_alerts": self.drowsy_alerts,
                    "sedentary_min": random.uniform(0, 35),
                    "status": "DROWSY" if ear < 0.21 else "OK",
                    "motion": random.random() > 0.3,
                    "face_detected": True,
                    "session_min": i * 0.5
                })
            print(f"[DEMO] Event: {evt} | EAR: {ear}")
        
        print("[DETECTOR] Demo hoàn tất. Xem dashboard tại http://127.0.0.1:5050")
        # Giữ live stats update
        while True:
            time.sleep(5)
    
    def get_live_stats(self) -> dict:
        with self._stats_lock:
            return dict(self.live_stats)

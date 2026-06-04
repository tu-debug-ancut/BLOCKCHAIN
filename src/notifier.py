"""
Notifier - Gửi thông báo hệ thống (Windows/Linux/Mac)
Hỗ trợ: plyer (cross-platform), win10toast (Windows), fallback print
"""

import sys
import threading
import time


class Notifier:
    
    URGENCY_COLORS = {
        "critical": "\033[91m",  # Đỏ
        "normal":   "\033[93m",  # Vàng
        "low":      "\033[96m",  # Cyan
    }
    RESET = "\033[0m"
    
    def __init__(self):
        self.backend = self._detect_backend()
        self.notification_history = []
        self._lock = threading.Lock()
        print(f"[NOTIFIER] Backend: {self.backend}")
    
    def _detect_backend(self) -> str:
        if sys.platform == "win32":
            try:
                from win10toast import ToastNotifier
                self._win_toaster = ToastNotifier()
                return "win10toast"
            except ImportError:
                pass
        
        try:
            from plyer import notification
            self._plyer_notif = notification
            return "plyer"
        except ImportError:
            pass
        
        if sys.platform == "linux":
            import shutil
            if shutil.which("notify-send"):
                return "notify-send"
        
        return "console"
    
    def send(self, title: str, message: str, urgency: str = "normal"):
        """Gửi thông báo (non-blocking)"""
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "title": title,
            "message": message,
            "urgency": urgency
        }
        with self._lock:
            self.notification_history.append(entry)
            if len(self.notification_history) > 100:
                self.notification_history.pop(0)
        
        t = threading.Thread(target=self._send_async, args=(title, message, urgency), daemon=True)
        t.start()
    
    def _send_async(self, title: str, message: str, urgency: str):
        try:
            color = self.URGENCY_COLORS.get(urgency, "")
            print(f"\n{color}🔔 [{urgency.upper()}] {title}{self.RESET}")
            print(f"   {message}\n")
            
            if self.backend == "win10toast":
                self._win_toaster.show_toast(
                    title, message,
                    duration=8,
                    threaded=True,
                    icon_path=None
                )
            
            elif self.backend == "plyer":
                self._plyer_notif.notify(
                    title=title,
                    message=message,
                    app_name="FatigueGuardian",
                    timeout=8
                )
            
            elif self.backend == "notify-send":
                import subprocess
                urgency_map = {"critical": "critical", "normal": "normal", "low": "low"}
                subprocess.Popen([
                    "notify-send",
                    f"--urgency={urgency_map.get(urgency,'normal')}",
                    "--expire-time=8000",
                    title, message
                ])
            
            # Âm thanh cảnh báo
            self._play_sound(urgency)
        
        except Exception as e:
            print(f"[NOTIFIER] Lỗi gửi thông báo: {e}")
    
    def _play_sound(self, urgency: str):
        """Phát âm thanh cảnh báo"""
        try:
            if sys.platform == "win32":
                import winsound
                if urgency == "critical":
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                else:
                    winsound.MessageBeep(winsound.MB_OK)
                return
        except Exception:
            pass
        
        try:
            import pygame
            pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            
            if urgency == "critical":
                freqs = [880, 0, 880, 0, 880]
                duration = 0.15
            elif urgency == "normal":
                freqs = [440, 550]
                duration = 0.2
            else:
                freqs = [330]
                duration = 0.3
            
            sample_rate = 22050
            for freq in freqs:
                if freq == 0:
                    time.sleep(0.05)
                    continue
                t_arr = __import__("numpy").linspace(0, duration, int(sample_rate * duration))
                wave = (32767 * __import__("numpy").sin(2 * __import__("numpy").pi * freq * t_arr)).astype(__import__("numpy").int16)
                sound = pygame.sndarray.make_sound(wave.reshape(-1, 1).repeat(2, axis=1) if pygame.mixer.get_init()[2] == 2 else wave)
                sound.play()
                time.sleep(duration + 0.02)
        except Exception:
            pass  # Âm thanh là tùy chọn
    
    def get_history(self) -> list:
        with self._lock:
            return list(reversed(self.notification_history))

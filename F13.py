import sys
import time
import ctypes
from datetime import datetime

# ========= CONFIG =========
STEALTH = False          # True = senza console (stealth), False = console + log
INTERVALLO_SEC = 180     # ogni quanti secondi premere F13
ORARIO_FINE = "18:00"    # "HH:MM" oppure None / "" per infinito
# =========================

VK_F13 = 0x7C
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

def hide_console():
    hwnd = kernel32.GetConsoleWindow()
    if hwnd:
        user32.ShowWindow(hwnd, 0)  # SW_HIDE = 0

def parse_end_time(hhmm: str):
    if not hhmm:
        return None
    now = datetime.now()
    end = datetime.strptime(hhmm, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
    return end

def end_reached(end_dt):
    return end_dt is not None and datetime.now() >= end_dt

def press_f13():
    # key down
    user32.keybd_event(VK_F13, 0, 0, 0)
    time.sleep(0.03)
    # key up
    user32.keybd_event(VK_F13, 0, KEYEVENTF_KEYUP, 0)

def main():
    if STEALTH:
        hide_console()

    end_dt = parse_end_time(ORARIO_FINE)

    if not STEALTH:
        print("Avviato. CTRL+C per uscire.")
        print(f"Intervallo: {INTERVALLO_SEC} sec")
        print(f"Orario fine: {ORARIO_FINE if ORARIO_FINE else '(nessuno)'}")

    try:
        while True:
            if end_reached(end_dt):
                if not STEALTH:
                    print("Orario di fine raggiunto. Uscita.")
                break

            press_f13()
            if not STEALTH:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] F13 premuto")

            time.sleep(INTERVALLO_SEC)

    except KeyboardInterrupt:
        if not STEALTH:
            print("\nInterrotto manualmente.")

if __name__ == "__main__":
    main()

import os
import sys
import time
import ctypes
import threading
import subprocess
from ctypes import wintypes
from datetime import datetime, timedelta


def relaunch_with_pythonw_if_needed():
    """Se avviato con python.exe, si ri-lancia con pythonw.exe (nessuna console) e chiude se stesso."""
    exe_name = os.path.basename(sys.executable).lower()
    if exe_name == "python.exe":
        pythonw_path = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        if os.path.exists(pythonw_path):
            subprocess.Popen(
                [pythonw_path, os.path.abspath(__file__)] + sys.argv[1:],
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            sys.exit(0)


relaunch_with_pythonw_if_needed()

# ========= CONFIG =========
INTERVALLO_SEC = 180     # ogni quanti secondi premere F13
ORARIO_FINE = "18:00"    # "HH:MM" oppure None / "" per infinito
# =========================

VK_F13 = 0x7C
KEYEVENTF_KEYUP = 0x0002

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shell32 = ctypes.windll.shell32

# ---------- Costanti Win32 ----------
WM_DESTROY = 0x0002
WM_CLOSE = 0x0010
WM_COMMAND = 0x0111
WM_APP = 0x8000
WM_TRAYICON = WM_APP + 1
WM_LBUTTONUP = 0x0202
WM_RBUTTONUP = 0x0205

NIM_ADD = 0x00000000
NIM_DELETE = 0x00000002
NIF_MESSAGE = 0x00000001
NIF_ICON = 0x00000002
NIF_TIP = 0x00000004

MF_STRING = 0x00000000
MF_GRAYED = 0x00000001
TPM_RIGHTALIGN = 0x0008
TPM_BOTTOMALIGN = 0x0020

IDI_APPLICATION = 32512
IDM_STATUS = 1001
IDM_EXIT = 1002

WS_OVERLAPPED = 0x00000000
WS_SYSMENU = 0x00080000
CW_USEDEFAULT = 0x80000000

# ---------- Strutture ----------
class WNDCLASS(ctypes.Structure):
    _fields_ = [
        ("style", ctypes.c_uint),
        ("lpfnWndProc", ctypes.c_void_p),
        ("cbClsExtra", ctypes.c_int),
        ("cbWndExtra", ctypes.c_int),
        ("hInstance", wintypes.HINSTANCE),
        ("hIcon", wintypes.HICON),
        ("hCursor", wintypes.HANDLE),
        ("hbrBackground", wintypes.HBRUSH),
        ("lpszMenuName", wintypes.LPCWSTR),
        ("lpszClassName", wintypes.LPCWSTR),
    ]

class NOTIFYICONDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("hWnd", wintypes.HWND),
        ("uID", wintypes.UINT),
        ("uFlags", wintypes.UINT),
        ("uCallbackMessage", wintypes.UINT),
        ("hIcon", wintypes.HICON),
        ("szTip", wintypes.WCHAR * 128),
    ]

LRESULT = ctypes.c_ssize_t

WNDPROCTYPE = ctypes.WINFUNCTYPE(
    LRESULT, wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM
)

# Dichiarazione esplicita di argtypes/restype per evitare overflow a 64-bit
user32.DefWindowProcW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
user32.DefWindowProcW.restype = LRESULT

user32.PostMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, wintypes.WPARAM, wintypes.LPARAM]
user32.PostMessageW.restype = wintypes.BOOL

user32.CreateWindowExW.argtypes = [
    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
]
user32.CreateWindowExW.restype = wintypes.HWND

user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASS)]
user32.RegisterClassW.restype = wintypes.ATOM

user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, ctypes.c_uint, ctypes.c_uint]
user32.GetMessageW.restype = ctypes.c_int

user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]
user32.DispatchMessageW.restype = LRESULT

user32.LoadIconW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.LoadIconW.restype = wintypes.HICON

user32.LoadCursorW.argtypes = [wintypes.HINSTANCE, ctypes.c_void_p]
user32.LoadCursorW.restype = wintypes.HANDLE

shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATA)]
shell32.Shell_NotifyIconW.restype = wintypes.BOOL

# ---------- Stato globale ----------
stop_event = threading.Event()
hwnd_global = None
nid_global = None


def parse_end_time(hhmm: str):
    if not hhmm:
        return None
    now = datetime.now()
    end_dt = datetime.strptime(hhmm, "%H:%M").replace(year=now.year, month=now.month, day=now.day)
    if end_dt <= now:
        # l'orario e' gia' passato oggi: evita che lo script si chiuda
        # subito dopo l'avvio, spostando la scadenza a domani.
        end_dt += timedelta(days=1)
    return end_dt


def end_reached(end_dt):
    return end_dt is not None and datetime.now() >= end_dt


def press_f13():
    user32.keybd_event(VK_F13, 0, 0, 0)
    time.sleep(0.03)
    user32.keybd_event(VK_F13, 0, KEYEVENTF_KEYUP, 0)


def f13_loop():
    end_dt = parse_end_time(ORARIO_FINE)
    while not stop_event.is_set():
        if end_reached(end_dt):
            break
        press_f13()
        for _ in range(INTERVALLO_SEC * 10):
            if stop_event.is_set():
                return
            time.sleep(0.1)
    # tempo scaduto: chiudi anche la tray
    if hwnd_global:
        user32.PostMessageW(hwnd_global, WM_CLOSE, 0, 0)


def show_tray_menu(hwnd):
    hmenu = user32.CreatePopupMenu()
    user32.AppendMenuW(hmenu, MF_STRING | MF_GRAYED, IDM_STATUS, "Stato: Avviato")
    user32.AppendMenuW(hmenu, MF_STRING, IDM_EXIT, "Esci")

    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))

    user32.SetForegroundWindow(hwnd)
    user32.TrackPopupMenu(hmenu, TPM_RIGHTALIGN | TPM_BOTTOMALIGN, pt.x, pt.y, 0, hwnd, None)
    user32.DestroyMenu(hmenu)


def wnd_proc(hwnd, msg, wparam, lparam):
    global nid_global

    if msg == WM_TRAYICON:
        if lparam in (WM_LBUTTONUP, WM_RBUTTONUP):
            show_tray_menu(hwnd)
        return 0

    elif msg == WM_COMMAND:
        cmd_id = wparam & 0xFFFF
        if cmd_id == IDM_EXIT:
            user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        return 0

    elif msg == WM_CLOSE:
        stop_event.set()
        if nid_global:
            shell32.Shell_NotifyIconW(NIM_DELETE, ctypes.byref(nid_global))
        user32.DestroyWindow(hwnd)
        return 0

    elif msg == WM_DESTROY:
        user32.PostQuitMessage(0)
        return 0

    return user32.DefWindowProcW(hwnd, msg, wparam, lparam)


def main():
    global hwnd_global, nid_global

    hinstance = kernel32.GetModuleHandleW(None)
    class_name = "F13SenderTrayClass"

    wndproc_func = WNDPROCTYPE(wnd_proc)

    wc = WNDCLASS()
    wc.style = 0
    wc.lpfnWndProc = ctypes.cast(wndproc_func, ctypes.c_void_p)
    wc.cbClsExtra = 0
    wc.cbWndExtra = 0
    wc.hInstance = hinstance
    wc.hIcon = user32.LoadIconW(None, ctypes.c_void_p(IDI_APPLICATION))
    wc.hCursor = user32.LoadCursorW(None, ctypes.c_void_p(32512))  # IDC_ARROW
    wc.hbrBackground = None
    wc.lpszMenuName = None
    wc.lpszClassName = class_name

    if not user32.RegisterClassW(ctypes.byref(wc)):
        raise ctypes.WinError()

    hwnd = user32.CreateWindowExW(
        0, class_name, "F13 Sender", WS_OVERLAPPED,
        CW_USEDEFAULT, CW_USEDEFAULT, 0, 0,
        None, None, hinstance, None
    )
    hwnd_global = hwnd

    # non mostriamo la finestra, serve solo per ricevere messaggi
    kernel32.GetConsoleWindow.restype = wintypes.HWND
    console_hwnd = kernel32.GetConsoleWindow()
    if console_hwnd:
        user32.ShowWindow(console_hwnd, 0)  # SW_HIDE

    nid = NOTIFYICONDATA()
    nid.cbSize = ctypes.sizeof(NOTIFYICONDATA)
    nid.hWnd = hwnd
    nid.uID = 1
    nid.uFlags = NIF_ICON | NIF_MESSAGE | NIF_TIP
    nid.uCallbackMessage = WM_TRAYICON
    nid.hIcon = wc.hIcon
    nid.szTip = "F13 Sender"
    nid_global = nid

    shell32.Shell_NotifyIconW(NIM_ADD, ctypes.byref(nid))

    t = threading.Thread(target=f13_loop, daemon=True)
    t.start()

    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))

    stop_event.set()
    t.join(timeout=2)


if __name__ == "__main__":
    main()

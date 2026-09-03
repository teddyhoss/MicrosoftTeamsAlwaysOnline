#!/usr/bin/env python3
"""
F13 Sender - versione macOS.

Equivalente di F13.py (Windows):
  - invia una pressione di F13 a intervalli regolari (resetta l'idle timer di sistema)
  - icona nella barra dei menu con voce "Esci"
  - orario di fine automatico
  - avvio silenzioso (processo staccato dal terminale, nessuna icona nel Dock)

L'invio dei tasti usa Quartz/CoreGraphics via ctypes: nessuna dipendenza esterna.
L'icona nella barra dei menu usa PyObjC (AppKit), incluso nel python3 di sistema
di macOS; se non e' disponibile lo script gira comunque in modalita' headless.

Richiede il permesso Accessibilita':
  Impostazioni di Sistema > Privacy e Sicurezza > Accessibilita'
  (autorizzare Terminale.app, oppure l'eseguibile Python usato per l'avvio)
"""

import os
import sys
import time
import ctypes
import ctypes.util
import signal
import threading
import subprocess
from datetime import datetime

# ========= CONFIG =========
INTERVALLO_SEC = 180        # ogni quanti secondi premere F13
ORARIO_FINE = "18:00"       # "HH:MM" oppure None / "" per infinito
AVVIO_SILENZIOSO = True     # True: si ri-lancia staccato dal terminale
# =========================

_ENV_DETACHED = "F13_DETACHED"

if sys.platform != "darwin":
    sys.stderr.write("Questo script e' la versione macOS. Su Windows usa F13.py.\n")
    sys.exit(1)


def relaunch_detached_if_needed():
    """Equivalente macOS del relaunch con pythonw.exe.

    Ri-lancia lo script in una nuova sessione, senza terminale collegato, e
    termina il processo corrente. La variabile d'ambiente evita il loop.
    """
    if not AVVIO_SILENZIOSO or os.environ.get(_ENV_DETACHED) == "1":
        return
    try:
        if not (sys.stdin and sys.stdin.isatty()):
            # gia' avviato senza terminale (launchd, .app, doppio clic)
            return
    except (ValueError, OSError):
        return

    env = dict(os.environ, **{_ENV_DETACHED: "1"})
    with open(os.devnull, "wb") as devnull:
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__)] + sys.argv[1:],
            stdin=devnull, stdout=devnull, stderr=devnull,
            start_new_session=True,
            env=env,
        )
    sys.exit(0)


relaunch_detached_if_needed()

# ---------- Quartz / CoreGraphics via ctypes ----------
kVK_F13 = 0x69                          # virtual keycode di F13 su macOS
kCGHIDEventTap = 0                      # posta l'evento a livello HID (resetta l'idle)
kCGEventSourceStateHIDSystemState = 1

_APPSERVICES_PATH = (
    ctypes.util.find_library("ApplicationServices")
    or "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
)
_COREFOUNDATION_PATH = (
    ctypes.util.find_library("CoreFoundation")
    or "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
)

appservices = ctypes.cdll.LoadLibrary(_APPSERVICES_PATH)
corefoundation = ctypes.cdll.LoadLibrary(_COREFOUNDATION_PATH)

appservices.CGEventSourceCreate.argtypes = [ctypes.c_int32]
appservices.CGEventSourceCreate.restype = ctypes.c_void_p

appservices.CGEventCreateKeyboardEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]
appservices.CGEventCreateKeyboardEvent.restype = ctypes.c_void_p

appservices.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
appservices.CGEventPost.restype = None

appservices.AXIsProcessTrusted.argtypes = []
appservices.AXIsProcessTrusted.restype = ctypes.c_bool

corefoundation.CFRelease.argtypes = [ctypes.c_void_p]
corefoundation.CFRelease.restype = None

# ---------- Stato globale ----------
stop_event = threading.Event()
event_source = None
app_delegate = None


def parse_end_time(hhmm):
    if not hhmm:
        return None
    now = datetime.now()
    return datetime.strptime(hhmm, "%H:%M").replace(year=now.year, month=now.month, day=now.day)


def end_reached(end_dt):
    return end_dt is not None and datetime.now() >= end_dt


def accessibility_check():
    """Avvisa se manca il permesso Accessibilita' (gli eventi verrebbero ignorati)."""
    if appservices.AXIsProcessTrusted():
        return True

    testo = (
        "F13 Sender non ha il permesso Accessibilita'.\n\n"
        "Apri Impostazioni di Sistema > Privacy e Sicurezza > Accessibilita' "
        "e autorizza l'app da cui avvii lo script (Terminale o Python).\n\n"
        "Senza questo permesso le pressioni di F13 vengono scartate dal sistema."
    )
    if sys.stderr and sys.stderr.isatty():
        print(testo, file=sys.stderr)
    else:
        try:
            subprocess.run(
                ["osascript", "-e",
                 'display dialog {} with title "F13 Sender" buttons {{"OK"}} default button 1'
                 .format(_applescript_quote(testo))],
                check=False, capture_output=True,
            )
        except OSError:
            pass
    return False


def _applescript_quote(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", '" & return & "') + '"'


def press_f13():
    """Invia keydown + keyup di F13 al livello HID."""
    global event_source
    if event_source is None:
        event_source = appservices.CGEventSourceCreate(kCGEventSourceStateHIDSystemState)

    for is_down in (True, False):
        evt = appservices.CGEventCreateKeyboardEvent(event_source, kVK_F13, is_down)
        if not evt:
            return
        appservices.CGEventPost(kCGHIDEventTap, evt)
        corefoundation.CFRelease(evt)
        if is_down:
            time.sleep(0.03)


def f13_loop():
    end_dt = parse_end_time(ORARIO_FINE)
    while not stop_event.is_set():
        if end_reached(end_dt):
            break
        press_f13()
        # attesa interrompibile: controlla lo stop ogni 100 ms
        for _ in range(INTERVALLO_SEC * 10):
            if stop_event.is_set():
                return
            time.sleep(0.1)
    # tempo scaduto: chiudi anche l'icona nella barra dei menu
    stop_event.set()
    if app_delegate is not None:
        app_delegate.performSelectorOnMainThread_withObject_waitUntilDone_(
            "terminaDaThread:", None, False
        )


# ---------- Modalita' barra dei menu (PyObjC) ----------
def run_menu_bar():
    from AppKit import (
        NSApplication,
        NSStatusBar,
        NSMenu,
        NSMenuItem,
        NSVariableStatusItemLength,
        NSApplicationActivationPolicyAccessory,
    )
    from Foundation import NSObject

    global app_delegate

    class F13AppDelegate(NSObject):

        def applicationDidFinishLaunching_(self, notification):
            self.statusItem = NSStatusBar.systemStatusBar().statusItemWithLength_(
                NSVariableStatusItemLength
            )
            button = self.statusItem.button()
            if button is not None:
                button.setTitle_("F13")
                button.setToolTip_("F13 Sender")

            menu = NSMenu.alloc().init()
            menu.setDelegate_(self)

            self.statoItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                self._testo_stato(), None, ""
            )
            self.statoItem.setEnabled_(False)
            menu.addItem_(self.statoItem)
            menu.addItem_(NSMenuItem.separatorItem())

            esciItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Esci", "esci:", "q"
            )
            esciItem.setTarget_(self)
            menu.addItem_(esciItem)

            self.statusItem.setMenu_(menu)

            self.worker = threading.Thread(target=f13_loop, daemon=True)
            self.worker.start()

        def _testo_stato(self):
            if ORARIO_FINE:
                return "Stato: avviato - fine {}".format(ORARIO_FINE)
            return "Stato: avviato - senza scadenza"

        # NSMenuDelegate: aggiorna il testo all'apertura del menu
        def menuWillOpen_(self, menu):
            if hasattr(self, "statoItem"):
                self.statoItem.setTitle_(self._testo_stato())

        def esci_(self, sender):
            self._spegni()

        def terminaDaThread_(self, sender):
            self._spegni()

        def applicationWillTerminate_(self, notification):
            stop_event.set()

        def _spegni(self):
            stop_event.set()
            if hasattr(self, "statusItem"):
                NSStatusBar.systemStatusBar().removeStatusItem_(self.statusItem)
            NSApplication.sharedApplication().terminate_(self)

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)  # nessuna icona nel Dock
    app_delegate = F13AppDelegate.alloc().init()
    app.setDelegate_(app_delegate)
    app.run()


# ---------- Modalita' headless (senza PyObjC) ----------
def run_headless():
    def handler(signum, frame):
        stop_event.set()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    t = threading.Thread(target=f13_loop, daemon=True)
    t.start()
    while t.is_alive() and not stop_event.is_set():
        t.join(timeout=0.5)
    stop_event.set()
    t.join(timeout=2)


def main():
    accessibility_check()

    try:
        import AppKit  # noqa: F401
        import Foundation  # noqa: F401
    except ImportError:
        run_headless()
    else:
        run_menu_bar()


if __name__ == "__main__":
    main()

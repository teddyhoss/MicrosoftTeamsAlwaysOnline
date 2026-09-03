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
import logging
from datetime import datetime

# ========= CONFIG =========
INTERVALLO_SEC = 180        # ogni quanti secondi premere F13
ORARIO_FINE = "18:00"       # "HH:MM" oppure None / "" per infinito
AVVIO_SILENZIOSO = True     # True: si ri-lancia staccato dal terminale
LOG_FILE = os.path.expanduser("~/Library/Logs/F13Sender.log")
# =========================

# --debug: resta in primo piano, log a video, intervallo breve.
DEBUG = "--debug" in sys.argv
if DEBUG:
    AVVIO_SILENZIOSO = False
    INTERVALLO_SEC = 5
    ORARIO_FINE = ""

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

# Idle di sistema: secondi dall'ultimo evento di input (qualsiasi tipo).
kCGAnyInputEventType = 0xFFFFFFFF
appservices.CGEventSourceSecondsSinceLastEventType.argtypes = [ctypes.c_int32, ctypes.c_uint32]
appservices.CGEventSourceSecondsSinceLastEventType.restype = ctypes.c_double

corefoundation.CFRelease.argtypes = [ctypes.c_void_p]
corefoundation.CFRelease.restype = None

# ---------- Stato globale ----------
stop_event = threading.Event()
event_source = None
app_delegate = None

log = logging.getLogger("f13")
pressioni = 0
ultima_pressione = None
ultimo_esito = "in attesa della prima pressione"


def setup_logging():
    """Log sempre su file; anche a video in --debug."""
    log.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s  %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        fh = logging.FileHandler(LOG_FILE)
        fh.setFormatter(fmt)
        log.addHandler(fh)
    except OSError as e:
        sys.stderr.write("Impossibile scrivere il log in {}: {}\n".format(LOG_FILE, e))
    if DEBUG:
        sh = logging.StreamHandler(sys.stdout)
        sh.setFormatter(fmt)
        log.addHandler(sh)


def idle_sistema():
    """Secondi dall'ultimo evento di input ricevuto dal sistema."""
    return appservices.CGEventSourceSecondsSinceLastEventType(
        kCGEventSourceStateHIDSystemState, kCGAnyInputEventType
    )


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
    """Invia keydown + keyup di F13 al livello HID.

    Verifica l'esito confrontando l'idle di sistema prima e dopo: se
    l'evento e' stato accettato l'idle si azzera. Se resta alto, macOS lo
    ha scartato (quasi sempre: manca il permesso Accessibilita').
    """
    global event_source, pressioni, ultima_pressione, ultimo_esito

    if event_source is None:
        event_source = appservices.CGEventSourceCreate(kCGEventSourceStateHIDSystemState)
        if not event_source:
            ultimo_esito = "ERRORE: impossibile creare la sorgente eventi"
            log.error(ultimo_esito)
            return False

    idle_prima = idle_sistema()

    for is_down in (True, False):
        evt = appservices.CGEventCreateKeyboardEvent(event_source, kVK_F13, is_down)
        if not evt:
            ultimo_esito = "ERRORE: creazione evento fallita"
            log.error(ultimo_esito)
            return False
        appservices.CGEventPost(kCGHIDEventTap, evt)
        corefoundation.CFRelease(evt)
        if is_down:
            time.sleep(0.03)

    time.sleep(0.05)  # lascia al sistema il tempo di registrare l'evento
    idle_dopo = idle_sistema()

    pressioni += 1
    ultima_pressione = datetime.now()
    ok = idle_dopo < idle_prima or idle_dopo < 1.0

    if ok:
        ultimo_esito = "OK (idle azzerato: {:.1f}s -> {:.1f}s)".format(idle_prima, idle_dopo)
        log.info("F13 #%d inviato - %s", pressioni, ultimo_esito)
    else:
        ultimo_esito = ("SCARTATO dal sistema (idle {:.1f}s -> {:.1f}s) - "
                        "manca il permesso Accessibilita'?".format(idle_prima, idle_dopo))
        log.warning("F13 #%d - %s", pressioni, ultimo_esito)
    return ok


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
    if not stop_event.is_set():
        log.info("orario di fine raggiunto: chiusura")
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

            self.statoItems = []
            for riga in self._righe_stato():
                it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(riga, None, "")
                it.setEnabled_(False)
                menu.addItem_(it)
                self.statoItems.append(it)
            menu.addItem_(NSMenuItem.separatorItem())

            logItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Apri il log...", "apriLog:", ""
            )
            logItem.setTarget_(self)
            menu.addItem_(logItem)
            menu.addItem_(NSMenuItem.separatorItem())

            esciItem = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
                "Esci", "esci:", "q"
            )
            esciItem.setTarget_(self)
            menu.addItem_(esciItem)

            self.statusItem.setMenu_(menu)

            self.worker = threading.Thread(target=f13_loop, daemon=True)
            self.worker.start()

        def _righe_stato(self):
            righe = ["Pressioni inviate: {}".format(pressioni)]
            if ultima_pressione:
                righe.append("Ultima: {}".format(ultima_pressione.strftime("%H:%M:%S")))
            righe.append("Esito: {}".format(ultimo_esito))
            righe.append("Idle di sistema: {:.0f}s".format(idle_sistema()))
            righe.append("Intervallo: {}s".format(INTERVALLO_SEC))
            righe.append("Fine: {}".format(ORARIO_FINE if ORARIO_FINE else "nessuna"))
            return righe

        # NSMenuDelegate: aggiorna i valori all'apertura del menu
        def menuWillOpen_(self, menu):
            for it, riga in zip(getattr(self, "statoItems", []), self._righe_stato()):
                it.setTitle_(riga)

        def apriLog_(self, sender):
            subprocess.Popen(["open", "-a", "Console", LOG_FILE])

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


def autotest():
    """Diagnostica: una pressione singola con verdetto esplicito. Esce subito."""
    print("=== F13 Sender - test ===")
    print("Python      : {}".format(sys.executable))
    trusted = appservices.AXIsProcessTrusted()
    print("Accessibilita': {}".format("OK" if trusted else "MANCANTE"))

    try:
        import AppKit  # noqa: F401
        print("PyObjC      : disponibile (icona nella barra dei menu)")
    except ImportError:
        print("PyObjC      : assente (modalita' headless)")

    print("Idle attuale: {:.1f}s".format(idle_sistema()))
    print("\nNON toccare tastiera e mouse per 3 secondi...")
    time.sleep(3)

    prima = idle_sistema()
    print("Idle prima di F13 : {:.1f}s".format(prima))
    press_f13()
    dopo = idle_sistema()
    print("Idle dopo F13     : {:.1f}s".format(dopo))

    if dopo < prima:
        print("\nFUNZIONA: l'idle si e' azzerato, il sistema ha accettato F13.")
        print("Teams ti vedra' attivo finche' lo script gira.")
        return 0

    print("\nNON FUNZIONA: l'idle non e' sceso, macOS ha scartato l'evento.")
    if not trusted:
        print("Causa: manca il permesso Accessibilita'.")
        print("Impostazioni di Sistema > Privacy e Sicurezza > Accessibilita'")
        print("e autorizza: {}".format(sys.executable))
        print("Dopo averlo dato, CHIUDI e riapri il Terminale.")
    else:
        print("Il permesso risulta concesso: prova a rimuovere e ri-aggiungere")
        print("l'app nell'elenco Accessibilita', poi riavvia il Terminale.")
    return 1


def main():
    if "--test" in sys.argv:
        setup_logging()
        sys.exit(autotest())

    setup_logging()

    trusted = appservices.AXIsProcessTrusted()
    log.info("--- avvio (pid %d, python %s) ---", os.getpid(), sys.executable)
    log.info("intervallo=%ss  fine=%s  accessibilita=%s  debug=%s",
             INTERVALLO_SEC, ORARIO_FINE or "nessuna",
             "OK" if trusted else "MANCANTE", DEBUG)

    accessibility_check()

    try:
        import AppKit  # noqa: F401
        import Foundation  # noqa: F401
    except ImportError:
        log.info("PyObjC non disponibile: modalita' headless")
        run_headless()
    else:
        log.info("modalita' barra dei menu")
        run_menu_bar()

    log.info("--- arresto (pressioni totali: %d) ---", pressioni)


if __name__ == "__main__":
    main()

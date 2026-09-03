# MicrosoftTeamsAlwaysOnline

> [English](#english) | [Italiano](#italiano)

---

<a name="english"></a>
# MicrosoftTeamsAlwaysOnline

A lightweight Python script that simulates an F13 keypress at a configurable interval to keep your status active on Microsoft Teams (or any app that tracks keyboard activity).

> **For educational purposes only.** This project demonstrates how to send synthetic keyboard events on Windows using the `ctypes` library.

---

## Features

- **Configurable interval** — set how often (in seconds) F13 is pressed
- **Auto stop time** — define an end time (`HH:MM`) after which the script stops automatically; leave blank to run indefinitely
- **System tray icon** — runs silently in the background with an icon in the Windows taskbar tray
- **Tray context menu** — right-click (or left-click) the tray icon to open a menu with status and exit option
- **Auto stealth launch** — if started with `python.exe`, the script automatically relaunches itself using `pythonw.exe` (no console window)
- **Responsive stop** — the F13 loop checks the stop signal every 100 ms, so exit is near-instant
- **Zero external dependencies** — uses only the Python standard library (`ctypes`, `threading`, `subprocess`, `datetime`)

---

## Requirements

- Windows (uses `ctypes.windll`)
- Python 3.6+

---

## Configuration

Edit the `CONFIG` section at the top of `F13.py`:

```python
INTERVALLO_SEC = 180      # interval between keypresses (seconds)
ORARIO_FINE    = "18:00"  # stop time "HH:MM", or "" / None to run forever
```

---

## Usage

```bash
python F13.py
```

The script automatically hides itself: if launched with `python.exe` it relaunches under `pythonw.exe` with no console window. A tray icon appears in the Windows taskbar — click it to see the status or exit.

To distribute as a single executable:

```bash
pyinstaller --noconsole --onefile F13.py
```

---

## How it works

```
startup:
    if running under python.exe → relaunch under pythonw.exe and exit
    register hidden window + tray icon
    start F13 loop on a background thread

loop (background thread):
    if current time >= ORARIO_FINE → post WM_CLOSE and exit
    send F13 keydown + keyup
    wait INTERVALLO_SEC seconds (interruptible every 100 ms)

tray menu:
    left/right click → show popup menu
    "Esci" → WM_CLOSE → remove tray icon, stop loop, quit
```

---

## macOS version

`F13_macos.py` is the macOS port. Same behaviour, different system APIs:

| | `F13.py` (Windows) | `F13_macos.py` (macOS) |
|---|---|---|
| Key event | `user32.keybd_event` | `CGEventPost` (Quartz, HID level) |
| Icon | Win32 tray icon | menu bar status item (`NSStatusBar`) |
| Silent launch | relaunch under `pythonw.exe` | relaunch detached via `start_new_session` |
| Event loop | `GetMessageW` message pump | `NSApplication.run()` |
| Dependencies | stdlib only | stdlib for the keypress; PyObjC for the menu bar icon |

### Requirements

- macOS 10.13+
- Python 3.6+
- **Accessibility permission**: System Settings > Privacy & Security > Accessibility,
  authorise the app you launch the script from (Terminal, or the Python binary).
  Without it macOS silently discards the synthetic keypresses.

### Usage

```bash
python3 F13_macos.py
```

### The menu bar icon

The icon sits at the top right and tells you the state at a glance, without
opening anything:

| Title | Meaning |
|---|---|
| `F13 ...` | started, first keypress not sent yet |
| `F13 * 12` | working — 12 keypresses accepted by the system |
| `F13 !` | the system is discarding the keypresses (see the menu) |
| `F13 x` | stopped |

Hovering shows a tooltip with the countdown to the next keypress. Click it for
the full status, an "Invia F13 adesso" entry to force a keypress and see the
counter move immediately, the log, and "Esci".

**The icon requires PyObjC**, which is NOT bundled with Homebrew or python.org
builds of Python (only the old system Python 2.7 had it). Without it the script
still works but shows no icon, so install it:

```bash
python3 -m pip install pyobjc-framework-Cocoa
```

If it is missing the script now says so explicitly instead of silently falling
back to headless mode.

### Is it working?

```bash
python3 F13_macos.py --test    # one keypress, explicit verdict, then exit
python3 F13_macos.py --debug   # foreground, 5 s interval, live log
```

`--test` reads the system idle timer before and after the keypress: if the idle
drops to zero the event was accepted, otherwise macOS discarded it (almost
always a missing Accessibility permission) and the output says how to fix it.

In normal mode the menu bar item shows the live counters (keypresses sent, last
one, outcome, current system idle) and everything is logged to:

```
~/Library/Logs/F13Sender.log
```

Independent check, from any terminal — this counts seconds since the last input
event, and it must never climb past your configured interval while the script
runs:

```bash
ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print $NF/1000000000 " s"}'
```

To distribute as a single executable:

```bash
pyinstaller --noconsole --onefile F13_macos.py
```

## Disclaimer

This tool is provided for **educational purposes** to demonstrate synthetic input and Win32 tray integration on Windows. Use it responsibly and in compliance with your organization's policies.

---
---

<a name="italiano"></a>
# MicrosoftTeamsAlwaysOnline

Uno script Python leggero che simula la pressione del tasto F13 a intervalli configurabili per mantenere attivo il proprio stato su Microsoft Teams (o qualsiasi app che rileva l'attivita' da tastiera).

> **Solo a scopo educativo.** Questo progetto dimostra come inviare eventi tastiera sintetici e integrare un'icona nella tray di Windows tramite la libreria `ctypes`.

---

## Funzionalita'

- **Intervallo configurabile** — imposta ogni quanti secondi viene premuto F13
- **Orario di fine automatico** — definisci un orario (`HH:MM`) oltre il quale lo script si ferma; lascia vuoto per eseguirlo a tempo indeterminato
- **Icona nella system tray** — gira silenziosamente in background con un'icona nella barra delle applicazioni di Windows
- **Menu contestuale tray** — clic destro (o sinistro) sull'icona per aprire un menu con stato e opzione di uscita
- **Avvio stealth automatico** — se avviato con `python.exe`, lo script si ri-lancia automaticamente con `pythonw.exe` (nessuna finestra console)
- **Stop reattivo** — il loop F13 controlla il segnale di stop ogni 100 ms, quindi l'uscita e' quasi istantanea
- **Zero dipendenze esterne** — utilizza solo la libreria standard di Python (`ctypes`, `threading`, `subprocess`, `datetime`)

---

## Requisiti

- Windows (usa `ctypes.windll`)
- Python 3.6+

---

## Configurazione

Modifica la sezione `CONFIG` in cima a `F13.py`:

```python
INTERVALLO_SEC = 180      # intervallo tra le pressioni (secondi)
ORARIO_FINE    = "18:00"  # orario di fine "HH:MM", oppure "" / None per infinito
```

---

## Utilizzo

```bash
python F13.py
```

Lo script si nasconde automaticamente: se avviato con `python.exe` si ri-lancia sotto `pythonw.exe` senza finestra console. Un'icona appare nella tray di Windows — cliccala per vedere lo stato o uscire.

Per distribuire come eseguibile singolo:

```bash
pyinstaller --noconsole --onefile F13.py
```

---

## Come funziona

```
avvio:
    se in esecuzione sotto python.exe → ri-lancia sotto pythonw.exe ed esci
    registra finestra nascosta + icona tray
    avvia il loop F13 su un thread in background

loop (thread background):
    se orario attuale >= ORARIO_FINE → invia WM_CLOSE ed esci
    invia F13 keydown + keyup
    attendi INTERVALLO_SEC secondi (interrompibile ogni 100 ms)

menu tray:
    clic sinistro/destro → mostra menu popup
    "Esci" → WM_CLOSE → rimuove icona tray, ferma loop, chiude
```

---

## Versione macOS

`F13_macos.py` e' il port per macOS. Stesso comportamento, API di sistema diverse:

| | `F13.py` (Windows) | `F13_macos.py` (macOS) |
|---|---|---|
| Evento tasto | `user32.keybd_event` | `CGEventPost` (Quartz, livello HID) |
| Icona | icona tray Win32 | voce nella barra dei menu (`NSStatusBar`) |
| Avvio silenzioso | ri-lancio con `pythonw.exe` | ri-lancio staccato con `start_new_session` |
| Loop eventi | message pump `GetMessageW` | `NSApplication.run()` |
| Dipendenze | solo stdlib | stdlib per la pressione; PyObjC per l'icona |

### Requisiti

- macOS 10.13+
- Python 3.6+
- **Permesso Accessibilita'**: Impostazioni di Sistema > Privacy e Sicurezza > Accessibilita',
  autorizzare l'app da cui si avvia lo script (Terminale, oppure il binario Python).
  Senza questo permesso macOS scarta silenziosamente le pressioni sintetiche.

### Utilizzo

```bash
python3 F13_macos.py
```

### L'icona nella barra dei menu

L'icona sta in alto a destra e dice lo stato a colpo d'occhio, senza aprire
nulla:

| Titolo | Significato |
|---|---|
| `F13 ...` | avviato, prima pressione non ancora inviata |
| `F13 * 12` | funziona — 12 pressioni accettate dal sistema |
| `F13 !` | il sistema sta scartando le pressioni (vedi il menu) |
| `F13 x` | fermato |

Passandoci sopra il mouse compare il conto alla rovescia alla prossima
pressione. Cliccandola trovi lo stato completo, la voce "Invia F13 adesso" per
forzare una pressione e vedere subito il contatore muoversi, il log e "Esci".

**L'icona richiede PyObjC**, che NON e' incluso nei Python di Homebrew o
python.org (lo aveva solo il vecchio Python 2.7 di sistema). Senza, lo script
funziona ma non mostra nessuna icona, quindi installalo:

```bash
python3 -m pip install pyobjc-framework-Cocoa
```

Se manca, ora lo script te lo dice esplicitamente invece di passare in
modalita' headless in silenzio.

### Come capire se sta funzionando

```bash
python3 F13_macos.py --test    # una pressione, verdetto esplicito, poi esce
python3 F13_macos.py --debug   # primo piano, intervallo 5 s, log a video
```

`--test` legge l'idle timer di sistema prima e dopo la pressione: se l'idle si
azzera l'evento e' stato accettato, altrimenti macOS lo ha scartato (quasi
sempre manca il permesso Accessibilita') e l'output spiega come rimediare.

In modalita' normale la voce nella barra dei menu mostra i contatori aggiornati
(pressioni inviate, ultima, esito, idle di sistema) e tutto viene registrato in:

```
~/Library/Logs/F13Sender.log
```

Verifica indipendente, da qualsiasi terminale — conta i secondi dall'ultimo
evento di input e non deve mai superare l'intervallo configurato mentre lo
script gira:

```bash
ioreg -c IOHIDSystem | awk '/HIDIdleTime/ {print $NF/1000000000 " s"}'
```

Per distribuire come eseguibile singolo:

```bash
pyinstaller --noconsole --onefile F13_macos.py
```

## Disclaimer

Questo strumento e' fornito a **scopo educativo** per dimostrare l'input sintetico e l'integrazione con la tray Win32 su Windows. Utilizzalo in modo responsabile e nel rispetto delle politiche della tua organizzazione.

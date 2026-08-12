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

## Disclaimer

Questo strumento e' fornito a **scopo educativo** per dimostrare l'input sintetico e l'integrazione con la tray Win32 su Windows. Utilizzalo in modo responsabile e nel rispetto delle politiche della tua organizzazione.

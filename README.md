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
- **Stealth mode** — hide the console window entirely for a background-only experience
- **Verbose logging** — when not in stealth mode, each keypress is logged with a timestamp
- **Clean exit** — supports `CTRL+C` for manual interruption at any time
- **Zero dependencies** — uses only the Python standard library (`ctypes`, `time`, `datetime`)

---

## Requirements

- Windows (uses `ctypes.windll`)
- Python 3.6+

---

## Configuration

Edit the `CONFIG` section at the top of `F13.py`:

```python
STEALTH        = False    # True  → hide console window
INTERVALLO_SEC = 180      # interval between keypresses (seconds)
ORARIO_FINE    = "18:00"  # stop time "HH:MM", or "" / None to run forever
```

---

## Usage

```bash
python F13.py
```

To run without a visible console window, set `STEALTH = True` before launching, or compile to an executable with a tool like PyInstaller:

```bash
pyinstaller --noconsole --onefile F13.py
```

---

## How it works

The script uses the Windows `user32.keybd_event` API to simulate pressing and releasing the F13 key (virtual key code `0x7C`). F13 is not bound to any default system action, so it acts as an invisible activity signal without interfering with your workflow.

```
loop:
    if current time >= ORARIO_FINE → exit
    send F13 keydown + keyup
    wait INTERVALLO_SEC seconds
```

---

## Disclaimer

This tool is provided for **educational purposes** to demonstrate synthetic input on Windows. Use it responsibly and in compliance with your organization's policies.

---
---

<a name="italiano"></a>
# MicrosoftTeamsAlwaysOnline

Uno script Python leggero che simula la pressione del tasto F13 a intervalli configurabili per mantenere attivo il proprio stato su Microsoft Teams (o qualsiasi app che rileva l'attivita' da tastiera).

> **Solo a scopo educativo.** Questo progetto dimostra come inviare eventi tastiera sintetici su Windows tramite la libreria `ctypes`.

---

## Funzionalita'

- **Intervallo configurabile** — imposta ogni quanti secondi viene premuto F13
- **Orario di fine automatico** — definisci un orario (`HH:MM`) oltre il quale lo script si ferma; lascia vuoto per eseguirlo a tempo indeterminato
- **Modalita' stealth** — nascondi completamente la finestra della console per un'esecuzione in background
- **Log verboso** — quando non e' in modalita' stealth, ogni pressione viene registrata con un timestamp
- **Uscita pulita** — supporta `CTRL+C` per l'interruzione manuale in qualsiasi momento
- **Zero dipendenze** — utilizza solo la libreria standard di Python (`ctypes`, `time`, `datetime`)

---

## Requisiti

- Windows (usa `ctypes.windll`)
- Python 3.6+

---

## Configurazione

Modifica la sezione `CONFIG` in cima a `F13.py`:

```python
STEALTH        = False    # True  → nascondi la finestra console
INTERVALLO_SEC = 180      # intervallo tra le pressioni (secondi)
ORARIO_FINE    = "18:00"  # orario di fine "HH:MM", oppure "" / None per infinito
```

---

## Utilizzo

```bash
python F13.py
```

Per eseguire senza finestra console visibile, imposta `STEALTH = True` prima di avviare, oppure compila in un eseguibile con PyInstaller:

```bash
pyinstaller --noconsole --onefile F13.py
```

---

## Come funziona

Lo script utilizza l'API Windows `user32.keybd_event` per simulare la pressione e il rilascio del tasto F13 (codice virtuale `0x7C`). F13 non e' associato a nessuna azione di sistema predefinita, quindi agisce come segnale di attivita' invisibile senza interferire con il flusso di lavoro.

```
loop:
    se orario attuale >= ORARIO_FINE → esci
    invia F13 keydown + keyup
    attendi INTERVALLO_SEC secondi
```

---

## Disclaimer

Questo strumento e' fornito a **scopo educativo** per dimostrare l'input sintetico su Windows. Utilizzalo in modo responsabile e nel rispetto delle politiche della tua organizzazione.

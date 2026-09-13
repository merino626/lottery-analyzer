<div align="center">

<img src="assets/icon.png" alt="Loterias da Caixa" width="96" />

# 🎲 Loterias da Caixa

**A local-first analytics, generator and checker for Brazil's national lottery draws — a public API, a resilient parallel sync engine, and a national pastime turned into inspectable data.**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.60-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Pandas](https://img.shields.io/badge/Pandas-2.x-150458?logo=pandas&logoColor=white)](https://pandas.pydata.org/)
[![SQLite](https://img.shields.io/badge/SQLite-local%20cache-003B57?logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![PyInstaller](https://img.shields.io/badge/PyInstaller-Windows%20.exe-3670A0?logo=windows&logoColor=white)](https://pyinstaller.org/)
[![pywebview](https://img.shields.io/badge/pywebview-native%20window-4B8BBE?logo=windows&logoColor=white)](https://pywebview.flowrl.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**English** · [Português (BR)](README.pt-BR.md)

</div>

> **New to Brazilian lotteries?** Skip straight to [Loterias da Caixa, for non-Brazilians](#loterias-da-caixa-for-non-brazilians) — the rest of this README will make a lot more sense with that context.

---

## Table of contents

- [Loterias da Caixa, for non-Brazilians](#loterias-da-caixa-for-non-brazilians)
- [Screenshots](#screenshots)
- [Why I built this](#why-i-built-this)
- [What it actually does](#what-it-actually-does)
- [Features](#features)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Engineering decisions worth calling out](#engineering-decisions-worth-calling-out)
- [Windows executable](#windows-executable)
- [Project structure](#project-structure)
- [Running it locally](#running-it-locally)
- [Disclaimer](#disclaimer)
- [Roadmap](#roadmap)
- [License](#license)

---

## Loterias da Caixa, for non-Brazilians

**Caixa Econômica Federal** is a large federal government-owned bank that, among other things, holds the legal monopoly on lottery games in Brazil — think of it as the closest local equivalent to a state lottery commission running Powerball or EuroMillions. Tickets cost a few reais, draws happen on live TV multiple times a week, and buying a ticket before a big jackpot is a genuinely mainstream national habit, not a niche hobby — closer to how a huge Powerball jackpot briefly becomes office small talk in the US, except it happens here on a regular schedule.

The flagship game is **Mega-Sena**: pick 6 numbers from 1–60, drawn every Wednesday and Saturday, with jackpots that regularly climb past R$ 100 million and occasionally much higher. "What would I do if I won the Mega-Sena" is a bar conversation on the same shelf as "what would you do if you won the lottery" anywhere else. But Caixa actually runs **eight** different games side by side, each with its own numbers, odds and personality:

| Game | Pick | From | What makes it different |
|---|---|---|---|
| **Mega-Sena** | 6 numbers | 1–60 | The flagship — biggest jackpots, twice a week |
| **Lotofácil** | 15 numbers | 1–25 | "Easy lotto" — much better odds, smaller, more frequent prizes |
| **Quina** | 5 numbers | 1–80 | Draws daily |
| **Lotomania** | 50 numbers | 0–99 | You pick 50 out of 100 — the *most* numbers of any game here |
| **Dupla-Sena** | 6 numbers | 1–50 | Two draws per contest — two chances to win from one ticket |
| **Timemania** | 10 numbers | 1–80 | Also pick a "Time do Coração" (favorite football club) — a slice of every ticket funds Brazilian football clubs |
| **+Milionária** | 6 numbers + 2 "trevos" | 1–50 + 1–6 | A secondary pick of two "clovers" (1–6), with a guaranteed minimum jackpot floor |
| **Dia de Sorte** | 7 numbers | 1–31 | Plus a "Mês da Sorte" (lucky month) pick |

This project talks to Caixa's own public results service, caches every draw of every game it supports locally, and gives that data a proper analytics/generator/checker interface. **No betting happens anywhere in this app** — see the [disclaimer](#disclaimer).

---

## Screenshots

### Switching lotteries re-runs every chart against that game's own history

Frequency, delay and the last jackpot are all recomputed live — Mega-Sena's 60-number spread looks nothing like Lotofácil's 25.

![Switching lottery](docs/screenshots/troca-modalidade.gif)

### Checking one ticket against 3,000+ past draws in about a second

Not just "would this have won the jackpot" — every prize tier the ticket would have hit, in every draw it was ever tested against, summed into one total.

![Checking a ticket against the full history](docs/screenshots/conferir-historico.gif)

### Análise — the full picture for one game

|                                          Overview                                          |                                        Frequency, delay & rankings                                        |
| :----------------------------------------------------------------------------------------------: | :------------------------------------------------------------------------------------------: |
| ![Analysis overview](docs/screenshots/analise.png)<br>_Contest count, last jackpot, and the latest prize breakdown by tier_ | ![Rankings](docs/screenshots/analise-rankings.png)<br>_How many contests since each number last appeared, plus hot/cold rankings_ |

### Concursos — drill into any single contest ever synced

![Contest detail](docs/screenshots/concursos.png)
_Numbers drawn, prize breakdown, and the full locally-cached history in one table._

### Gerador — random or frequency-weighted tickets, checked against history on the spot

![Generator](docs/screenshots/gerador.png)
_Generates a ticket and immediately reports whether it would already have won something, and how much._

### Conferidor — check one contest, or your entire local history

![Checker](docs/screenshots/conferidor.png)
_Paste one ticket per line; check it against the latest draw, a specific one, or everything downloaded so far._

_The interface itself is in Brazilian Portuguese — screenshots above are the real app with real, publicly synced historical data (no mock data anywhere)._

---

## Why I built this

Checking last week's numbers against "what I would've won if..." is a very Brazilian pastime, and I wanted to turn that curiosity into something I could actually interrogate: does number 10 *really* come up more in Mega-Sena, or does it just feel that way? How rare is it, really, for a simple 6-number pick to have hit *any* prize tier across 3,000+ historical draws?

It's also a small, complete showcase of a few things that don't show up in a typical CRUD demo:

- a sync engine that treats "what's missing" as a **set difference**, not "one number higher than the last save" — so it self-heals from holes left by a flaky public API instead of just chasing the latest contest;
- graceful, deliberate degradation under rate limiting instead of hammering a server that already asked us to slow down;
- a matching rule that would rather report "unknown" than confidently attribute the wrong prize value; and
- one codebase that runs identically as a local dev server (`streamlit run app.py`) and as a **double-clickable Windows .exe**, with a single, well-isolated difference between the two: where the cache file lives.

And — being upfront about it, the way the [disclaimer](#disclaimer) below also is — number frequency in a fair lottery draw is *not* predictive of future draws. Past frequency and "how long since a number last appeared" are real, honestly computed statistics about the past; nothing here claims they forecast the future. The generator's "frequency-weighted" mode exists because it's a fun, common strategy people actually use, not because there's evidence it beats picking numbers at random — each draw is independent of the last.

---

## What it actually does

The app opens as a local Streamlit page with **four tabs**, all scoped to whichever of the eight games is picked in the sidebar:

1. **Análise** — syncs the full contest history for the selected game from Caixa's public API into a local SQLite cache (parallel downloads, resumable), then shows frequency and "delay" (contests since last seen) per number, hot/cold rankings, and the latest synced contest's full prize breakdown plus the next contest's accumulated jackpot.
2. **Concursos** — look up any individual contest ever cached: numbers drawn, date, whether it rolled over, and the complete prize table for every tier, right down to how much each winner actually received.
3. **Gerador** — generate one or many tickets, either uniformly at random or weighted by historical frequency, and optionally see on the spot how many times that exact ticket would already have won *something* in the synced history, and how much, with a filter to restrict the check to specific prize tiers.
4. **Conferidor** — paste one or more tickets and check them either against a single contest (the latest, or any specific one) or against **the entire synced history at once**, listing every contest where that ticket would have hit a prize, the tier, the payout, and the running total.

---

## Features

### 🔄 Sync engine
- Downloads missing contests in parallel (5 concurrent requests by default) via a `ThreadPoolExecutor` — a several-thousand-contest game like Quina or Lotofácil would take a very long time one request at a time.
- "What's missing" is computed as **the full set of contest numbers minus what's already cached**, not just "anything after the highest saved contest" — so a sync that got interrupted mid-way (leaving holes in the middle of the history) is repaired correctly on the next run, not just extended at the end.
- If Caixa's API starts responding with `429`/`403` (rate limiting) repeatedly, the sync **stops itself** after a run of consecutive failures instead of grinding for minutes — whatever was already downloaded is kept, and the next sync resumes exactly where it left off.
- Each request retries with exponential backoff plus jitter before being counted as a failure.

### 📊 Analysis
- Per-number frequency and "delay" (how many contests since it last appeared) across the entire local history.
- Hot/cold rankings (most drawn, least drawn, most overdue).
- Even/odd split and average sum per draw.
- The latest synced contest's full prize table — winners and payout per tier — plus the next contest's accumulated jackpot and draw date.

### 🎯 Generator
- Two strategies: uniform random, or weighted sampling **without replacement** by historical frequency (a proper weighted draw, not "sample with replacement and hope for no duplicates").
- Optional duplicate-avoidance across a batch of generated tickets.
- Optional instant check of each generated ticket against the full local history, with a prize-tier filter.

### ✅ Checker
- Check any number of tickets, one per line, against a single contest or the entire local history at once.
- Matches against **every** prize tier a ticket's hit count corresponds to — not just the top ("jackpot") tier — so a 4-number match in a Mega-Sena ticket is correctly reported even though the "main" prize is 6 matches.
- Full-history mode lists every contest a ticket would have won something in, the tier, the payout, and the summed total.

### 🖥️ Runs two ways from one codebase
- As a normal local web app: `streamlit run app.py`.
- As a standalone Windows **.exe** — see [below](#windows-executable) — no Python install required for whoever runs it.

---

## Tech stack

| | |
|---|---|
| **Streamlit** | The entire UI — sidebar, tabs, charts, tables, forms — no separate frontend build. |
| **Pandas** | Shapes query results into the tables and bar charts Streamlit renders. |
| **SQLite** (stdlib `sqlite3`) | Local cache of every synced contest — one file, zero setup, trivially portable. |
| **Requests** | Talks to Caixa's public (unofficial) lottery results API, with retry/backoff on top. |
| **`concurrent.futures.ThreadPoolExecutor`** (stdlib) | Parallelizes the download of missing contests — this is I/O-bound HTTP work, so threads are the right tool, no async rewrite needed. |
| **PyInstaller** | Packages the app plus a small launcher into a standalone Windows `.exe`. |
| **pywebview** | Embeds the UI in a real native window (Windows' own WebView2/Edge Chromium) for the desktop build — no visible browser, no console. |

No web framework, no ORM, no task queue — a data-analysis app like this doesn't need one, and Streamlit's own server is the entire backend.

---

## Architecture

```
                              BROWSER (localhost)
                                     │
                          ┌──────────▼───────────┐
                          │        app.py         │   4 tabs, one sidebar (choose game)
                          └──────────┬───────────┘
                                     │
        ┌───────────────┬───────────┼───────────────┬────────────────┐
        ▼                ▼           ▼               ▼                │
   analysis.py     generator.py  checker.py       sync.py              │
   frequency,      random /      score a ticket   parallel download,   │
   delay, ranks    weighted      vs. 1 or all      gap-aware resume    │
        │                │      contests             │                │
        └────────────────┴─────────────┬─────────────┘                │
                                        ▼                               │
                                 storage.py (SQLite)                    │
                                        │                               │
                          data/resultados.db, or                       │
                     %APPDATA%/LoteriasDaCaixa/ when frozen ◄──────────┘
                                        ▲
                                        │ HTTP, retry + backoff (api.py)
                                        │
                        Caixa's public lottery results API
```

Every module talks to `storage.py`, never to `api.py` and `storage.py` directly at once — `sync.py` is the only place that writes fresh API results into the cache; everything else (`analysis`, `generator`, `checker`) only ever reads from SQLite. That split is what makes "sync once, analyze/generate/check instantly and offline afterwards" possible.

---

## Engineering decisions worth calling out

**Gap-aware sync, not just "resume from the last save."** `_concursos_faltantes` computes `{1 .. latest} - {already cached}` as an actual set difference, every time. Caixa's API occasionally starts refusing requests mid-sync, which can leave holes in the *middle* of the history even though the most recent contest was saved first. Resuming from "the highest saved contest number" would silently skip those holes forever; the set-difference approach finds and fills them on the very next sync.

**The sync gives up on purpose.** After `FALHAS_SEGUIDAS_LIMITE` (8) consecutive failed requests — the signature of the API rate-limiting the client — the sync raises `SincronizacaoParcial` instead of continuing to retry for minutes. Everything downloaded up to that point is already saved; the user is told plainly what happened and that re-running later resumes correctly. Fighting a server that already said "slow down" helps no one.

**A regex that deliberately refuses to match.** `_PADRAO_ACERTOS` only matches "pure" prize descriptions like `"6 acertos"` — never `"6 acertos + 2 trevos"` (the two-clover bonus tier in +Milionária). Two different prize tiers can share the same raw hit count but differ by an extra criterion (a "trevo" or a "Time do Coração" pick) this app doesn't track. Matching loosely there would have silently attributed the wrong tier's payout to a ticket. Reporting "acertos = None" (untracked) for that tier was the deliberately less-convenient, more-correct choice.

**Full-tier checking, not just the jackpot.** `conferir_no_historico` checks a ticket's hit count against *every* prize tier a contest paid out, not only the top tier for that game. A 4-number match on a Mega-Sena ticket is a real, paid prize tier — a checker that only reported jackpot-or-nothing would tell a winning ticket it lost.

**Weighted sampling without replacement, done properly.** The frequency-weighted generator strategy (`_amostra_ponderada_sem_reposicao`) re-normalizes the remaining weights and re-draws after each pick, rather than the much easier but statistically wrong shortcut of sampling with replacement and discarding duplicates (which skews the effective weighting, especially as `k` approaches the size of the pool, as it does for Lotomania's 50-out-of-100).

**One code path, two runtimes.** `storage.DB_PATH` resolves differently depending on `sys.frozen`: a normal `data/resultados.db` next to the project when run with `streamlit run app.py`, or a persistent `%APPDATA%/LoteriasDaCaixa/resultados.db` when running as the packaged `.exe`. This one existed for a concrete reason: PyInstaller's `--onefile` mode extracts the whole app into a **temporary directory that's deleted when the process exits** — without this split, the .exe would silently re-download its entire cache from scratch on every single launch.

**A native window and a background server can't share one main thread — so they don't share a process.** The desktop build embeds the UI in a real OS window via `pywebview` (Windows' own WebView2/Edge Chromium engine), and pywebview's event loop must own the main thread. Streamlit's own bootstrap *also* insists on the main thread — it registers a `SIGTERM` handler on startup, which Python only allows there. Running Streamlit on a background thread instead raises `ValueError: signal only works in main thread of the main interpreter`. The fix: `desktop_launcher.py` re-executes itself as a **subprocess** with a hidden flag; the parent's main thread runs the window, the child's main thread runs Streamlit — each gets the main thread it insists on, because each is a different process.

**An orphaned server process, closed with a Windows Job Object.** Splitting the app into two processes creates a cleanup problem: what stops the Streamlit subprocess if the parent window process is killed outright (crash, Task Manager, a forced shutdown) rather than closed normally? A `finally: processo.terminate()` never runs in that case — it's Python code, and a killed process doesn't get to run its own cleanup. The actual fix lives one level below Python: the child is assigned to a Windows *Job Object* created with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`, so the OS kernel itself guarantees the child dies the instant the parent's handle to the job is gone — including a hard kill the parent never sees coming. Verified by force-killing the parent mid-session and confirming the server process and its WebView2 helper processes all disappear with it, instead of lingering as invisible background processes.

**Latin-1, not UTF-8.** Caixa's API serves accented text (Portuguese, naturally) encoded as latin-1 while declaring nothing reliable in its headers; decoding as UTF-8 by default corrupts every accented character in prize descriptions and dates. `api.py` sets `resposta.encoding = "latin-1"` explicitly before parsing the JSON body.

**Additive, idempotent schema migration.** `storage._migrar` inspects `PRAGMA table_info` and adds any of three columns (added after the original schema) that are missing, tolerating a cache file created by an older version of the app instead of forcing a wipe.

---

## Windows executable

The exact same codebase also ships as a standalone desktop app — no Python installation required, no terminal, no browser tab to find: double-click `LoteriasDaCaixa.exe` and a real window opens with the app already running inside it.

### How it works

[`desktop_launcher.py`](desktop_launcher.py) is the entry point PyInstaller builds. On launch it:

1. picks a free local port and re-executes itself as a **subprocess**, passing a hidden flag that tells that copy to just run `streamlit run app.py` on that port (see [why a subprocess and not a thread](#engineering-decisions-worth-calling-out) above);
2. waits for the port to answer, then opens a real native window via **`pywebview`** (Windows' built-in WebView2/Edge Chromium engine) pointed straight at it — no address bar, no browser chrome, no separate tab;
3. if WebView2 isn't available for any reason, falls back to opening the system's default browser instead of failing outright;
4. ties the Streamlit subprocess to a Windows Job Object so it can never outlive the window, even if the app is force-closed.

The result behaves like an ordinary desktop app: one process shows up in the taskbar, one window, no console.

### Build it yourself

```bash
pip install -r requirements.txt -r requirements-desktop.txt
python build_exe.py
```

This produces `dist/LoteriasDaCaixa/` — a **folder**, not a single file (PyInstaller's `--onedir` mode: faster to start than `--onefile`, and this app in particular launches a second copy of itself as a subprocess every run, which would mean extracting a onefile bundle twice). `LoteriasDaCaixa.exe` inside that folder is what you actually run; to share it, zip the whole folder. Nothing under `dist/`/`build/` is committed — `build_exe.py` regenerates it from scratch every time, using [`assets/icon.ico`](assets/icon.ico) as the executable's icon.

> The `.exe` is unsigned (no paid code-signing certificate), so Windows SmartScreen will likely show a **"Windows protected your PC"** warning the first time it runs. Click **More info → Run anyway**, or just build it yourself from source with the commands above so you know exactly what's in it.

### What to expect at runtime

- WebView2 ships with Windows 10 (21H2+) and Windows 11 by default, so this normally just works; on an older or stripped-down install without it, the app opens in your default browser instead (see step 3 above) rather than failing.
- Your synced lottery data persists across runs in `%APPDATA%\LoteriasDaCaixa\resultados.db` (see the [architecture](#architecture) section above for why this differs from the dev-mode path) — deleting that folder resets the cache exactly like the in-app "wipe and re-sync" button does.

---

## Project structure

```
loterias/
├── app.py                    # Streamlit UI — sidebar + the 4 tabs, no business logic
├── desktop_launcher.py       # entry point for the packaged .exe (subprocess split + native pywebview window)
├── build_exe.py              # reproducible PyInstaller build (`python build_exe.py`)
├── requirements.txt          # to run the app: `streamlit run app.py`
├── requirements-desktop.txt  # extra deps only needed to build the .exe (pyinstaller, pywebview)
│
├── loteria/                  # all business logic — importable and independently testable
│   ├── api.py                 # HTTP client for Caixa's public API: retry/backoff, latin-1 handling, response parsing
│   ├── modalidades.py         # static config for the 8 supported games (ranges, pick counts, API slugs)
│   ├── sync.py                 # gap-aware, parallel, rate-limit-aware sync into SQLite
│   ├── storage.py              # SQLite persistence + schema migration; resolves dev vs. packaged DB path
│   ├── analysis.py             # frequency, delay, rankings, even/odd/sum stats
│   ├── generator.py             # random / frequency-weighted ticket generation
│   └── checker.py               # score a ticket against one contest or the full history, any prize tier
│
├── assets/
│   ├── icon.ico                 # Windows .exe icon
│   └── icon.png                 # same icon, used in this README
│
├── docs/screenshots/            # everything embedded above in this README
│
└── data/                        # local SQLite cache — created automatically, not committed (see .gitignore)
```

---

## Running it locally

### Prerequisites

- Python 3.11+ (developed and tested against it; other 3.x versions likely work too)

### Installation

```bash
git clone https://github.com/merino626/lottery-analyzer.git
cd lottery-analyzer
pip install -r requirements.txt
```

### Run

```bash
streamlit run app.py
```

Opens automatically at `http://localhost:8501`. Pick a game in the sidebar, hit **Sincronizar** on the Análise tab to download its history (this can take a little while the very first time for the larger games — Quina alone has 7,000+ contests), and the other three tabs come alive from that local cache.

---

## Disclaimer

This is an independent, unofficial hobby project with **no affiliation with, endorsement by, or connection to** Caixa Econômica Federal. It reads publicly available contest results from Caixa's own results service purely for historical analysis; it does not use any private or authenticated API.

**No real betting, wagering or money transfer of any kind happens anywhere in this application.** "Gerador" produces number combinations for entertainment purposes only, and "Conferidor" only compares numbers you type in against historical results already drawn in the past — it does not submit, place or influence any bet. Official results, prize amounts and drawing schedules always come from [caixa.gov.br](https://loterias.caixa.gov.br/) — treat this app's cached data as a convenience for exploration, not as an authoritative or real-time source.

Lottery games are a form of gambling: every draw is an independent random event, past frequency does not predict future draws, and the house edge means the expected value of playing is negative over time. If lottery play stops being fun, Brazil's National Council of Justice and various public health services provide free support for problem gambling.

---

## Roadmap

- [ ] Track "trevos" (+Milionária) and "Time do Coração" (Timemania) as first-class criteria, so their prize tiers can be matched automatically instead of appearing as "untracked"
- [ ] Support both draws of Dupla-Sena (currently only the first is stored/checked)
- [ ] Automated tests for `loteria/` (currently verified manually against real synced data)
- [ ] macOS/Linux packaging (PyInstaller supports it; only the Windows build has been produced so far)

---

## License

Released under the [MIT License](LICENSE) — © 2026 Luis Eduardo.

<div align="center">

Built by [@merino626](https://github.com/merino626) — a side project born from a very Brazilian habit of checking "would I have won?"

</div>

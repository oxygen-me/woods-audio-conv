# Multimedia Superutility — v0.1.0

Windows-first, local-first multimedia utility.

> If your computer can do it, you shouldn't need a website to do it.

## v0.1.0 goal

This is the first vertical slice:

**Drop a media file → inspect it → choose an output → convert/remux → validate → record history.**

The architecture deliberately separates:

- **Media Model** — what the file is
- **Capability Model** — what can be done
- **Operation Model** — what the user wants
- **Execution Plan** — how it will be done
- **Backend** — performs the work
- **Job** — manages execution
- **Validation** — decides whether the result is actually good
- **History** — records what happened

FFmpeg/ffprobe are external runtime tools. Put them in `runtime/` for development:

```text
runtime/
  ffmpeg.exe
  ffprobe.exe
```

The application does not execute shell strings. Backend translators produce argument vectors.

## Development

Requires exactly CPython 3.14.6 x64 on Windows.

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -U pip
.venv\Scripts\python.exe -m pip install -e .
```

Run:

```powershell
.venv\Scripts\python.exe -m superutility
```

Or:

```powershell
.venv\Scripts\superutility.exe
```

## Runtime

Core inspection and conversion expect:

```text
runtime\ffmpeg.exe
runtime\ffprobe.exe
```

If they are missing, the UI will still launch and explain the missing runtime.

## Scope

v0.1.0 intentionally does **not** attempt to implement the entire superutility.

Included:
- Windows GUI shell
- drag/drop and file picker
- ffprobe-backed inspection
- MediaFile model
- capability evaluation for basic operations
- structured conversion/remux operations
- FFmpeg argument translation
- background job execution
- progress display
- output validation
- SQLite history
- Unicode/space-safe process execution

Next:
- richer stream selection
- audio extraction UI
- batch jobs
- recipes
- thumbnails/waveforms
- acquisition/download providers
- image backend
- advanced custom codec/container workspace
- installer/portable packaging

# Changelog

All notable changes to this project are documented here.
This project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [4.0.0] - 2026-08-17

First public release of the cleaned, portable wrapper. This release is a
privacy/portability overhaul: the application code is unchanged in behaviour
except where noted under *Fixed*.

### Added
- **Privacy & Security section in the README**, documenting verified localhost-only
  egress, absence of telemetry/update checks, `asInvoker` manifest, and the one
  user-controlled risk (`--listen 0.0.0.0` in *Custom Launch Args*).
- **Known limitations section** stating plainly that the EXE is unsigned (SmartScreen
  guidance included), the engine is not bundled, an NVIDIA GPU is expected, and that
  `tests/qa_audit.py` is a static audit rather than an image-quality test.
- **`requirements.lock.txt`** with fully pinned (`==`) dependencies, verified by
  installing into a clean virtual environment.
- **`Setup.bat`** installer/uninstaller that provisions the app without hardcoded
  user paths and places an existing local engine next to the EXE.
- **`--selftest` boot verification** used to prove the frozen EXE initialises its
  UI and application state cleanly.
- **`COMFYUI_PORTABLE_DIR` environment override** for explicitly locating the engine.
- **Debug tab** wired into the interface.

### Changed
- **Executable and spec renamed** from the legacy `ComfyUIX` naming to
  `ComfyUI_Uncensored.exe` / `ComfyUI_Uncensored.spec`.
- **Engine location is now resolved, not hardcoded.** Resolution order:
  `COMFYUI_PORTABLE_DIR` (wins unconditionally) → sibling `ComfyUI_windows_portable`
  → parent/cwd candidates → legacy absolute paths as a last-resort fallback only.
  Frozen builds anchor on the executable's real directory instead of the temporary
  extraction directory.
- **All filesystem paths derive from `expanduser` + `normpath`**, so output, log, and
  Tcl/Tk locations follow the current user instead of a fixed machine path.
- **Build metadata (`build_info.json`) uses a stable project identity** rather than the
  local checkout folder name, which would otherwise leak the developer's directory layout.
- **`.gitignore` hardened** to exclude build artifacts, scratch files, virtual
  environments, and assistant/agent workspaces.

### Fixed
- Frozen builds failed to import `numpy._core`; resolved via explicit submodule
  collection in the PyInstaller spec.
- A non-existent engine sampler key was referenced in the UI wiring and has been removed.
- `tests/qa_audit.py` now reports **127 checks, 127 passing**.

### Security
- **Git history rewritten** to remove personal identifying information (developer
  username, real name, and organisation identifiers) from *all* prior commits, along
  with previously published scratch and agent-tooling files. Commit authorship was
  normalised. Verified afterwards: zero real-identity matches across every reachable blob.
- **Working tree and shipped binary verified free of personal data.** The frozen EXE was
  audited by decompressing its embedded Python archive and scanning both bundled module
  source strings and raw bundled files. The only residual match was the string
  `Go Daddy` inside the bundled `certifi` CA store — a certificate-authority vendor name,
  not personal data. The scanner excludes only that audited string in only that file; a
  negative control (a different CA name) still fails the scan, confirming the exclusion
  cannot mask a genuine leak.
- Wrapper remains **MIT**; the GPL-3.0 ComfyUI runtime is not redistributed, keeping the
  two licences independent.

[4.0.0]: https://github.com/Bonbrake/App/releases/tag/v4.0.0

# HyperSolve

A Windows desktop browser assistant built with Python, PyQt6, and Playwright.

## Windows app

The app opens to a light workspace with a dark navigation rail. The workspace uses an ink/cobalt identity and a tab/check icon. It starts stopped: nothing is selected or submitted merely by opening the app.

1. Open **Connections → Open workspace browser**. Google Chrome is required.
2. Sign in to ChatGPT, Gemini, or Claude in that browser. An open provider tab is detected; detection alone does not verify sign-in.
3. Open the page you want to work with in the same browser.
4. In **Workspace**, choose the tab and select **Start session**. The session reads questions, sends them to an available AI provider, selects matching answers, and navigates pages. Review the outcome in Chrome.
5. For continuing automation, choose **Automatic quiz detection** and click **Start automation**. It watches open tabs for supported quiz structures, processes new quizzes, and keeps watching until you stop it. It does not start automatically on app launch. If a page is not detected, use **Selected tab** mode.
6. Use **Stop** to cancel. Closing the app stops the session and leaves Chrome open. Keeping it in the tray is an optional setting.

The parser contains adapters for several question formats plus DOM heuristics. Compatibility and answer correctness vary with the page and provider. No accuracy percentage is fabricated, and no claim of universal compatibility or undetectability is made.

## Saved workspace

In **Connections → Saved workspace**, choose **Save workspace** to snapshot open HTTP/HTTPS tabs and the selected source locally in `%LOCALAPPDATA%\HyperSolve\workspace.json`. This replaces the previous snapshot atomically. Cookies and passwords are not copied; sign-ins remain in Chrome's dedicated profile.

**Restore workspace** opens missing tabs and keeps existing tabs. It does not start automation. Page history, unsaved form entries, tab groups, and window positions are not part of this snapshot. Redirected tabs are reconciled while the browser session remains open. A tab that cannot load is reported without preventing the rest from reopening. Quitting stops the remaining restore queue; an active navigation can take up to 10 seconds to finish or time out.

## Install

Use `HyperSolve-Setup-v2.2.0.exe` from a built release or `dist_installer/`. Python and application dependencies are bundled. Install is per-user and does not require administrator access. Start Menu shortcuts and uninstall support are included; Desktop and Windows-login shortcuts are optional.

New browser profiles and logs live under `%LOCALAPPDATA%\HyperSolve`. A source checkout reuses its existing `chrome_profile` when present. Updates and uninstall preserve browser data. No profile, cookies, credentials, or local logs belong in a release artifact.

The app has one instance per Windows user. Launching it again restores the existing window. `--tray` starts in the tray when available.

## Run from source

Windows x64 and Python 3.12+:

```powershell
python -m pip install -r requirements.txt
python main.py
```

`run_dashboard.bat` and `run_tray.bat` are convenience launchers. The browser engine remains available as `python main.py --engine`. The separate legacy screenshot HUD runs through `desktop_main.py`; it is not integrated into the new desktop workspace or bundled default entry point.

Optional `GEMINI_API_KEY` and `OPENAI_API_KEY` environment variables enable API fallback. Browser sessions do not require API keys. The desktop does not store API keys in its settings.

## Build a standalone installer

Install the packages above plus PyInstaller and Inno Setup 6, then run:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_windows.ps1
```

The script runs offline tests, renders the authored SVG icon into Windows ICO resolutions, bundles `dist/HyperSolve/`, builds the installer, and writes `dist_installer/latest.json` with its SHA-256 checksum. `setup.bat` launches a built installer; it never installs shortcuts linked to a source checkout.

The GitHub Windows workflow runs the same build for branches and PRs. A version tag matching `hypersolve/__version__.py` publishes the installer and checksum manifest. Without a trusted release manifest, the update client refuses installation. Failed checks are shown as failures, not as “up to date”.

The installer is currently unsigned. A code-signing certificate and signing credentials are not configured.

## Verify

```powershell
python -m unittest discover -s tests -v
```

Offline tests use mocked browser and provider connections. They do not establish live-provider compatibility, model accuracy, or screen-capture behaviour. Logs are available from **Settings → Open log folder**.

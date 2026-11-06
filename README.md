# HyperSolve

A Windows desktop browser assistant built with Python, PyQt6, and Playwright.

## Windows app

The app opens to a native **Browser manager** with observed counts for working agents, pending approvals, selected answers, and review flags. The light workspace and dark navigation rail retain HyperSolve’s ink/cobalt identity.

### Everyday Chrome and Edge (3.0)

1. Install `HyperSolve-Setup-v3.0.0.exe` and open the manager. The installer registers its native bridge for your Windows account.
2. In **Manager**, click **Open extension folder**. Open `chrome://extensions` or `edge://extensions`, enable Developer mode, choose **Load unpacked**, and select that `browser-extension` folder. This is a one-time manual setup. HyperSolve does not change browser security settings or install an extension silently.
3. Open the companion popup and choose **Connect Windows manager**. Reload existing quiz/provider tabs once if needed. Detection starts automatically on supported HTTP/HTTPS pages, including newly opened tabs. Internal pages, cross-origin embedded quizzes, and incognito are not monitored.
4. A visible glass panel reports **Quiz detected**, visible question count, and a total when exposed by the page. Choose **Start solving**, or approve the row in Windows. Detection sends only page metadata/counts to Windows; questions go to AI only after approval.
5. Each tab has an independent agent, pause/stop controls, answer explanations, and progress. It scans supported Next pages, validates exact choices, and leaves missing, ambiguous, or uncertain answers for review. Companion mode never presses Finish or Submit.
6. API jobs have three concurrent slots. Browser AI jobs use new conversations and queue per provider to avoid sharing a prompt box. Open and sign in to ChatGPT, Gemini, or Claude first; provider UI/authentication can still require attention.

**Pause** holds the next action; a request already sent can finish. Closing a quiz tab cancels that agent. Leaving its approved quiz scope stops it. Interrupted work stops safely after a browser/worker/manager restart; scan again from the popup to create a new session. Monitoring can be toggled in the popup.

The popup can save the current window’s web tabs/pinned state locally and restore them in a new window. Cookies, passwords, history, and unsaved form inputs are not copied. The bridge uses an authenticated loopback endpoint and an extension allowlist. API credentials are never stored in the extension. **Repair browser connection** re-registers a built bridge if needed. Keep the unpacked folder in its installed location.

### Dedicated workspace browser (legacy workflow)

1. Open **Connections → Open workspace browser**. Google Chrome is required.
2. Sign in to ChatGPT, Gemini, or Claude in that browser. An open provider tab is detected; detection alone does not verify sign-in.
3. Open the page you want to work with in the same browser.
4. In **Workspace**, choose the tab and select **Start session**. The session reads questions, sends them to an available AI provider, selects matching answers, and navigates pages. Review the outcome in Chrome.
5. For continuing automation, choose **Automatic quiz detection** and click **Start automation**. It watches open tabs for supported quiz structures, processes new quizzes, and keeps watching until you stop it. It does not start automatically on app launch. If a page is not detected, use **Selected tab** mode.
6. Use **Stop** to cancel. Closing the app stops the session and leaves Chrome open. Keeping it in the tray is an optional setting.

The parser contains adapters for several question formats plus DOM heuristics. Compatibility and answer correctness vary with the page and provider. No accuracy percentage is fabricated, and no claim of universal compatibility or undetectability is made.

## Visible browser overlay

During a session, HyperSolve shows a visible cobalt panel on the quiz page. It remains through page navigation and displays harvesting, AI waiting, selection progress, current question, and selected answers.

- **Pause / Resume:** holds the next page action. An AI request already sent may finish while paused; no subsequent selection/navigation proceeds until resumed.
- **Stop:** cancels the running session, including Watch mode.
- **Show question:** scrolls to the current question when it is on this page.
- **Copy answers:** copies the displayed selected answers; the browser may restrict clipboard access.
- **Collapse / Expand:** changes panel size without hiding session controls.
- Drag the header, or focus it and use arrow keys, to reposition the panel. Position is remembered for the site while its browser session remains open.

The panel is visible in the page; no capture-exclusion or undetectability claim is made. Closing or stopping a session leaves the results visible with processing controls disabled.

## Saved workspace

In **Connections → Saved workspace**, choose **Save workspace** to snapshot open HTTP/HTTPS tabs and the selected source locally in `%LOCALAPPDATA%\HyperSolve\workspace.json`. This replaces the previous snapshot atomically. Cookies and passwords are not copied; sign-ins remain in Chrome's dedicated profile.

**Restore workspace** opens missing tabs and keeps existing tabs. It does not start automation. Page history, unsaved form entries, tab groups, and window positions are not part of this snapshot. Redirected tabs are reconciled while the browser session remains open. A tab that cannot load is reported without preventing the rest from reopening. Quitting stops the remaining restore queue; an active navigation can take up to 10 seconds to finish or time out.

## Install

Use `HyperSolve-Setup-v3.0.0.exe` from a built release or `dist_installer/`. Python, the native bridge, and the unpacked companion are bundled; a companion ZIP is also built. Install is per-user and does not require administrator access. Start Menu shortcuts and uninstall support are included; Desktop and Windows-login shortcuts are optional.

New browser profiles and logs live under `%LOCALAPPDATA%\HyperSolve`. A source checkout reuses its existing `chrome_profile` when present. Updates and uninstall preserve browser data. No profile, cookies, credentials, or local logs belong in a release artifact.

The app has one instance per Windows user. Launching it again restores the existing window. `--tray` starts in the tray when available.

## Run from source

Windows x64 and Python 3.12+:

```powershell
python -m pip install -r requirements.txt
python main.py
```

`run_dashboard.bat` and `run_tray.bat` are convenience launchers. The browser engine remains available as `python main.py --engine`. The separate legacy screenshot HUD runs through `desktop_main.py`; it is not integrated into the new desktop workspace or bundled default entry point.

Optional `GEMINI_API_KEY` and `OPENAI_API_KEY` environment variables enable API solving (preferred for companion tasks when configured). `HYPERSOLVE_OPENAI_MODEL` and `HYPERSOLVE_GEMINI_MODEL` override companion model IDs. Restart the manager after changing environment variables. Browser sessions do not require API keys. The desktop does not store API keys. Source mode can register the bridge after a Windows build through **Repair browser connection**.

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
python scripts/smoke_companion.py
```

The companion smoke requires the Windows build and `python -m playwright install chromium`. It uses an isolated bundled-Chromium profile, temporarily registers the built native bridge, restores the previous registration, and tests local quizzes plus stub API/provider pages. It checks approval, independent tabs, pause, multi-page saving, exact selection, and no submission. These checks do not establish live-provider compatibility or model accuracy. Logs are available from **Settings → Open log folder**.

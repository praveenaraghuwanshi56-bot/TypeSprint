# TypeSprint for Windows: one exe, offline, self-updating

The result is **one file, `TypeSprint.exe`**. Double-click to run; no installer. It shows your website in a native
window (Edge WebView2), with fonts and scripts bundled so it opens offline. It updates itself from GitHub.

## What works offline
| Works offline | Needs internet |
|---|---|
| Typing tests, 7 games, lessons, themes, "My runs", downloads | Sign-in, accounts, leaderboard, saving scores |
| Wikipedia/Datamuse features use the built-in fallback lists | Fresh Wikipedia passages and Datamuse words |

Offline and not signed in: the app starts you as a guest. Signed in before: you stay signed in.
Progress is saved in `%LOCALAPPDATA%\TypeSprint\` and survives updates.

## Easiest way: let GitHub build the exe (no Python on your PC)
1. Unzip this package **into the root of your TypeSprint repo**, so you have `index.html`, `desktop/` and
   `.github/` side by side. Upload/commit them to GitHub (`.github` is a hidden-looking folder; drag it in too).
2. Edit `desktop/src/version.py` and replace `YOUR-GITHUB-NAME` in `UPDATE_URL` with your GitHub name
   (and the repo name if it is not `TypeSprint`). **The repo must be public** for auto-update to work.
3. On GitHub: **Actions**, then **Build Windows app**, then **Run workflow**. Wait about 5 minutes.
4. Open the repo's **Releases** page and download `TypeSprint.exe`. That is the file you give to people.

## Releasing an update (for example after Arena AI changes the website)
1. Commit the new `index.html` to the repo.
2. Raise `__version__` in `desktop/src/version.py` (1.0.0 to 1.0.1) and commit.
3. Run the workflow again (type what's new in the "notes" box).
Everyone's app notices on its next launch: "TypeSprint 1.0.1 is available. Install now?" Yes: it downloads,
checks the SHA-256 fingerprint, swaps the exe and reopens. No: it won't ask again for that version.

## Building on your own PC instead
Install Python 3.10+ (tick "Add to PATH"), put the `desktop/` folder next to `index.html`, double-click
`desktop\build.bat`. Result: `desktop\dist\TypeSprint.exe`. For updates by hand run
`python tools\make_release.py --repo YOU/TypeSprint --notes "..."` and upload `TypeSprint.exe` + `version.json`
to a GitHub Release tagged `v<version>`.

## Honest limits
- **Windows parts are untested.** I tested here: the site/fonts/scripts are bundled and served correctly by a
  one-file build (on Linux), the update check, download, checksum and exe-swap logic. The window itself, WebView2,
  and the GitHub workflow have not been run. The workflow runs a built-in self-check (`TypeSprint.exe --selftest`)
  and refuses to publish if it fails.
- **Antivirus / SmartScreen:** unsigned one-file exes sometimes get a "Windows protected your PC" warning
  (More info, then Run anyway) or a false alarm. Only a paid code-signing certificate fully removes this.
- **Slower first second:** a one-file exe unpacks itself on every launch (about 1 to 3 seconds).
- **Updating needs the exe in a folder the user can write to** (Desktop, Documents, Downloads: fine; Program Files: not).
- The checksum guards against corrupted downloads, not against someone taking over your GitHub account.
- One copy at a time (it uses local port 47831 so saved progress keeps the same address).
- Please test one run-log download early; it depends on pywebview's download support.
- The old per-user installer idea was dropped in favour of the single exe. It can be added back if you want.

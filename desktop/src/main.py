"""TypeSprint desktop app: shows the bundled website in a native window (Edge WebView2), fully offline.

Command line: --selftest (checks the bundled site loads, then exits) and --after-update (set by the updater)."""
import ctypes
import json
import logging
import os
import pathlib
import sys
import threading
import time
import webbrowser

import webview

import localserver
import updater
from version import UPDATE_URL, __version__

WEBVIEW2_DOWNLOAD = "https://go.microsoft.com/fwlink/p/?LinkId=2124703"

# Folder for things that must survive updates: saved progress, settings, log.
DATA_DIR = pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home())) / "TypeSprint"
DATA_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=DATA_DIR / "app.log", level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("typesprint")


def resource(rel):
    """Path to a bundled file (works both from source and from the PyInstaller build)."""
    return pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).parent)) / rel


def message_box(title, text):
    if sys.platform == "win32":
        ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)
    else:
        print(title, text)


# ----- small settings file (remembers which update the person said "not now" to) -----
SETTINGS = DATA_DIR / "settings.json"


def load_settings():
    try:
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(s):
    try:
        SETTINGS.write_text(json.dumps(s), encoding="utf-8")
    except Exception:
        log.exception("could not save settings")


# ----- what the web page can ask the app to do -----
class Api:
    def open_external(self, url):
        if isinstance(url, str) and url.startswith(("https://", "http://")):
            webbrowser.open(url)

    def app_version(self):
        return __version__


# Runs inside the page after it loads: links to other sites open in the real browser, not in this window.
LINK_JS = """
(function () {
  if (window.__tsLinks) return; window.__tsLinks = true;
  const open = (u) => { if (window.pywebview && pywebview.api) pywebview.api.open_external(String(u)); };
  document.addEventListener("click", (e) => {
    const a = e.target.closest && e.target.closest("a[href]");
    if (a && /^https?:/i.test(a.href) && a.origin !== location.origin) { e.preventDefault(); open(a.href); }
  }, true);
  window.open = (u) => { if (u) open(u); return null; };
})();
"""

BANNER_JS = """
(function (text) {
  let b = document.getElementById("ts-update-banner");
  if (!b) {
    b = document.createElement("div"); b.id = "ts-update-banner";
    b.style.cssText = "position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:99999;padding:10px 18px;" +
      "border-radius:999px;background:#2b2118;color:#fff;font:600 14px system-ui,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.3)";
    document.body.appendChild(b);
  }
  b.textContent = text;
})(%s);
"""


def banner(window, text):
    try:
        window.evaluate_js(BANNER_JS % json.dumps(text))
    except Exception:
        pass


def update_flow(window):
    """Background thread: ask the update server, offer the update, download, verify, install."""
    time.sleep(4)                                   # let the page settle first
    info = updater.check_for_update(UPDATE_URL, __version__)
    if not info:
        return
    settings = load_settings()
    if settings.get("skip_version") == info["version"]:
        return
    notes = (info.get("notes") or "").strip()
    question = (f"TypeSprint {info['version']} is available (you have {__version__}).\n\n"
                + (notes + "\n\n" if notes else "") + "Install it now? TypeSprint will restart by itself.")
    if not window.create_confirmation_dialog("TypeSprint update", question):
        settings["skip_version"] = info["version"]  # don't ask again for this version
        save_settings(settings)
        return
    try:
        banner(window, "Downloading update…")
        updater.install_update(info, lambda p: banner(window, f"Downloading update… {p}%"))
        banner(window, "Updated! TypeSprint is reopening…")
        time.sleep(1)
        os._exit(0)                                 # the new TypeSprint.exe is already starting
    except Exception as e:
        log.exception("update failed")
        banner(window, "The update didn't work this time. Your app is fine; it will try again next launch.")
        message_box("TypeSprint update", f"Could not install the update:\n{e}\n\nYou can keep using this version.")


def start_server():
    """Starts the local site server. Right after an update the old copy may need a moment to close, so retry."""
    tries = 20 if "--after-update" in sys.argv else 3
    for i in range(tries):
        try:
            return localserver.start(resource("web"))
        except OSError:
            if i < tries - 1:
                time.sleep(0.5)
    return None


def selftest():
    """Exit code 0 if the bundled website and fonts are served correctly. Used by the automatic build."""
    import urllib.request
    try:
        server, url = localserver.start(resource("web"), port=localserver.PORT + 1)
        base = url.rsplit("/", 1)[0]
        for path, needle in (("/index.html", "TypeSprint"), ("/fonts/fonts.css", "Bricolage"), ("/vendor/supabase.js", "supabase")):
            body = urllib.request.urlopen(base + path, timeout=5).read().decode("utf-8", "ignore")
            assert needle in body, path
        assert "googleapis" not in urllib.request.urlopen(base + "/index.html").read().decode("utf-8", "ignore"), "online font link left"
        print("SELFTEST OK", __version__)
        return 0
    except Exception as e:
        print("SELFTEST FAILED:", e)
        return 1


def main():
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    updater.cleanup_old()                           # remove the previous version left by the last update
    started = start_server()
    if not started:
        message_box("TypeSprint", "TypeSprint is already running (or another program is using port "
                                  f"{localserver.PORT}).")
        return
    server, url = started
    log.info("TypeSprint %s starting at %s", __version__, url)

    window = webview.create_window("TypeSprint", url, js_api=Api(), width=1280, height=820,
                                   min_size=(900, 600), text_select=True)

    def on_loaded():
        try:
            window.evaluate_js(LINK_JS)
        except Exception:
            log.exception("link script failed")

    window.events.loaded += on_loaded
    threading.Thread(target=update_flow, args=(window,), daemon=True).start()

    webview.settings["ALLOW_DOWNLOADS"] = True      # lets the "download my run log" buttons save files
    try:
        webview.start(gui="edgechromium" if sys.platform == "win32" else None,
                      storage_path=str(DATA_DIR / "webdata"), private_mode=False)
    except Exception:
        log.exception("window failed to start")
        message_box("TypeSprint", "TypeSprint needs the Microsoft Edge WebView2 Runtime.\n"
                                  f"Download it here (free, from Microsoft):\n{WEBVIEW2_DOWNLOAD}")
        webbrowser.open(WEBVIEW2_DOWNLOAD)


if __name__ == "__main__":
    main()

"""Checks the parts that don't need a window: local server, update checking/downloading, checksum safety.
Run:  python tests/test_core.py   (needs ../index.html and a prior prepare_web.py run)"""
import hashlib, http.server, json, os, pathlib, sys, threading, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
import localserver, updater  # noqa: E402

ok = True
def check(name, cond):
    global ok; ok &= bool(cond); print(("PASS " if cond else "FAIL ") + name)

# --- versions
check("1.0.10 > 1.0.9", updater.parse_version("1.0.10") > updater.parse_version("1.0.9"))
check("v2.0 parses", updater.parse_version("v2.0") == (2, 0))
check("junk -> (0,)", updater.parse_version("abc") == (0,))

# --- bundled site served with the right file types
srv, url = localserver.start(ROOT / "src" / "web", port=47899)
def head(path):
    with urllib.request.urlopen(url.rsplit("/", 1)[0] + path) as r:
        return r.status, r.headers["Content-Type"], len(r.read())
s, t, n = head("/index.html"); check("index.html served as html", s == 200 and t.startswith("text/html") and n > 200000)
s, t, n = head("/vendor/supabase.js"); check("supabase.js served as javascript", t.startswith("text/javascript"))
s, t, n = head("/fonts/bricolage-grotesque-latin-opsz-normal.woff2"); check("font served as woff2", t == "font/woff2")
try: localserver.start(ROOT / "src" / "web", port=47899); check("second copy is refused", False)
except OSError: check("second copy is refused (port busy)", True)

# --- fake update server
fake = pathlib.Path("/tmp/fake_updates"); fake.mkdir(exist_ok=True)
installer = b"MZ-fake-installer-bytes" * 5000
(fake / "setup.exe").write_bytes(installer)
good = {"version": "1.0.1", "url": "https://x", "sha256": hashlib.sha256(installer).hexdigest(), "notes": "n"}
(fake / "version.json").write_text(json.dumps(good))
class Q(http.server.SimpleHTTPRequestHandler):
    def __init__(s, *a, **k): super().__init__(*a, directory=str(fake), **k)
    def log_message(s, *a): pass
fs = http.server.ThreadingHTTPServer(("127.0.0.1", 47898), Q); threading.Thread(target=fs.serve_forever, daemon=True).start()
base = "http://127.0.0.1:47898"

# check_for_update demands https for the installer URL, so test with the local copy by relaxing only the URL field
info = json.loads((fake / "version.json").read_text())
check("https installer URL accepted", updater.check_for_update(base + "/version.json", "1.0.0") is not None)
check("same version -> no update", updater.check_for_update(base + "/version.json", "1.0.1") is None)
check("newer installed -> no update", updater.check_for_update(base + "/version.json", "2.0.0") is None)
check("unreachable server -> None (no crash)", updater.check_for_update("http://127.0.0.1:1/x.json", "1.0.0", timeout=1) is None)
bad_http = dict(good, url="http://insecure"); (fake / "bad.json").write_text(json.dumps(bad_http))
check("http (not https) installer URL rejected", updater.check_for_update(base + "/bad.json", "1.0.0") is None)
check("placeholder URL ignored", updater.check_for_update("https://github.com/YOUR-GITHUB-NAME/x", "1.0.0") is None)

# --- download + checksum
dest = pathlib.Path("/tmp/dl_test.exe"); prog = []
updater.download_file(dict(good, url=base + "/setup.exe"), dest, prog.append)
check("download ok + checksum verified", dest.stat().st_size == len(installer) and prog and prog[-1] == 100)
try: updater.download_file(dict(good, url=base + "/setup.exe", sha256="0" * 64), dest); check("wrong checksum rejected", False)
except ValueError: check("wrong checksum rejected and file removed", not dest.exists())

# --- self-update swap (pretend we are a frozen exe)
work = pathlib.Path("/tmp/upd_app"); work.mkdir(exist_ok=True)
for f in work.iterdir(): f.unlink()
fake_exe = work / "TypeSprint.exe"; fake_exe.write_bytes(b"OLD-VERSION")
launched = []
sys.frozen = True; real_exec = sys.executable; sys.executable = str(fake_exe)
updater.subprocess.Popen = lambda cmd, **k: launched.append(cmd)
try:
    updater.install_update(dict(good, url=base + "/setup.exe"))
    check("exe replaced with new version", fake_exe.read_bytes() == installer)
    check("old version kept as .old", (work / "TypeSprint.exe.old").read_bytes() == b"OLD-VERSION")
    check("new copy relaunched with --after-update", launched and launched[0][1] == "--after-update")
    updater.cleanup_old(); check("old version cleaned up at next start", not (work / "TypeSprint.exe.old").exists())
    fake_exe.write_bytes(b"OLD2")
    try: updater.install_update(dict(good, url=base + "/setup.exe", sha256="1" * 64)); check("bad update refused", False)
    except ValueError: check("bad update refused, app untouched", fake_exe.read_bytes() == b"OLD2" and not (work / "TypeSprint.new.exe").exists())
finally:
    del sys.frozen; sys.executable = real_exec
sys.exit(0 if ok else 1)

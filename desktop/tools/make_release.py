"""After the exe is built: writes dist/version.json describing dist/TypeSprint.exe.

The GitHub build runs this for you. By hand:
  python tools/make_release.py --repo yourname/TypeSprint --notes "Faster Wordle, small fixes"
then create a GitHub Release tagged v<version> and upload BOTH dist/TypeSprint.exe and dist/version.json.
(The app reads  https://github.com/<repo>/releases/latest/download/version.json )
"""
import argparse, hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from version import __version__  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--repo", help="GitHub 'owner/name' that will host the release")
ap.add_argument("--url", help="full https URL of the installer, if not using GitHub Releases")
ap.add_argument("--notes", default="")
a = ap.parse_args()

exe = ROOT / "dist" / "TypeSprint.exe"
if not exe.exists():
    sys.exit(f"Not found: {exe}. Build the exe first.")
url = a.url or (f"https://github.com/{a.repo}/releases/download/v{__version__}/TypeSprint.exe" if a.repo else None)
if not url:
    sys.exit("Give --repo owner/name (GitHub) or --url https://...")
info = {"version": __version__, "url": url, "sha256": hashlib.sha256(exe.read_bytes()).hexdigest(), "notes": a.notes}
out = ROOT / "dist" / "version.json"
out.write_text(json.dumps(info, indent=2), encoding="utf-8")
print("wrote", out); print(json.dumps(info, indent=2))

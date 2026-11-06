"""Checks for a newer version and replaces the running TypeSprint.exe with it.

version.json looks like:
  {"version": "1.0.1", "url": "https://.../TypeSprint.exe", "sha256": "<64 hex characters>", "notes": "What's new"}
Safety rules: the download must be https, and its SHA-256 must match the value in version.json.
"""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import urllib.request


def parse_version(text):
    """'1.2.10' -> (1, 2, 10). Anything unreadable -> (0,)."""
    try:
        return tuple(int(p) for p in str(text).strip().lstrip("vV").split("."))
    except ValueError:
        return (0,)


def check_for_update(update_url, current_version, timeout=6):
    """Returns the version.json dict if a newer, well-formed release exists; otherwise None (also when offline)."""
    if not update_url or "YOUR-GITHUB-NAME" in update_url:
        return None
    try:
        req = urllib.request.Request(update_url, headers={"User-Agent": "TypeSprint-Desktop"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            info = json.loads(r.read().decode("utf-8"))
        if parse_version(info["version"]) <= parse_version(current_version):
            return None
        if not str(info["url"]).startswith("https://") or len(str(info["sha256"])) != 64:
            return None
        return info
    except Exception:
        return None


def download_file(info, dest, progress=None):
    """Downloads info['url'] to dest and checks its SHA-256. Deletes the file and raises if anything is wrong."""
    sha = hashlib.sha256()
    req = urllib.request.Request(info["url"], headers={"User-Agent": "TypeSprint-Desktop"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length") or 0)
            done = 0
            while True:
                chunk = r.read(256 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                sha.update(chunk)
                done += len(chunk)
                if progress and total:
                    progress(int(done * 100 / total))
        if sha.hexdigest().lower() != str(info["sha256"]).lower():
            raise ValueError("The downloaded update did not match its checksum, so it was discarded.")
    except Exception:
        try:
            os.remove(dest)
        except OSError:
            pass
        raise
    return dest


def self_path():
    return pathlib.Path(sys.executable)


def cleanup_old():
    """Deletes the previous version left behind by the last update (called at start-up)."""
    try:
        old = self_path().with_name(self_path().name + ".old")
        if old.exists():
            old.unlink()
    except OSError:
        pass


def install_update(info, progress=None):
    """Downloads the new TypeSprint.exe next to the current one, swaps them, and starts the new one.

    Windows lets a running .exe be renamed (not deleted), so: current -> TypeSprint.exe.old, new -> TypeSprint.exe.
    The caller should exit right after this returns.
    """
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Updates only work in the packaged TypeSprint.exe.")
    exe = self_path()
    new = exe.with_name(exe.stem + ".new" + exe.suffix)
    old = exe.with_name(exe.name + ".old")
    download_file(info, new, progress)
    try:
        if old.exists():
            old.unlink()
        os.replace(exe, old)
        try:
            os.replace(new, exe)
        except OSError:
            os.replace(old, exe)            # put the working copy back
            raise
    except OSError as e:
        try:
            os.remove(new)
        except OSError:
            pass
        raise RuntimeError(f"Could not replace the app file (is it in a protected folder?): {e}")
    flags = 0x00000008 | 0x00000200 if sys.platform == "win32" else 0   # DETACHED_PROCESS | NEW_PROCESS_GROUP
    subprocess.Popen([str(exe), "--after-update"], close_fds=True, creationflags=flags)

"""Turns the website's index.html (repo root) into the offline desktop copy (src/web/index.html).

Run this every time the website changes (build.bat and the GitHub build do it for you). It only makes small, exact
replacements and stops with a clear message if the website no longer contains the text it expects.
"""
import pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT.parent / "index.html"        # the website file in the repo root, next to the desktop/ folder
if not SRC.exists():
    sys.exit(f"STOP: website file not found at {SRC}. Put the desktop/ folder inside your TypeSprint repo, next to index.html.")
OUT = ROOT / "src" / "web" / "index.html"

html = SRC.read_text(encoding="utf-8")


def replace_once(text, old, new, what):
    if text.count(old) != 1:
        sys.exit(f"STOP: could not find the {what} in index.html exactly once "
                 f"(found {text.count(old)}). The website changed; the script needs a small update.")
    return text.replace(old, new)


# 1. Google Fonts -> local fonts (three <link> lines near the top of <head>)
start = html.index('<link rel="preconnect" href="https://fonts.googleapis.com">')
end = html.index("rel=\"stylesheet\">", html.index("fonts.googleapis.com/css2")) + len("rel=\"stylesheet\">")
html = html[:start] + '<link rel="stylesheet" href="fonts/fonts.css">' + html[end:]

# 2. Supabase script from the internet -> bundled copy
html = replace_once(
    html,
    '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js"></script>',
    '<script src="vendor/supabase.js"></script>',
    "Supabase <script> tag")

# 3. Desktop flag + "no internet and not signed in: just start as a guest" (runs before the main script)
shim = """<script>
window.TS_DESKTOP = true;
try { if (!navigator.onLine && !localStorage.getItem("ts-session")) sessionStorage.setItem("ts-guest", "1"); } catch (e) {}
</script>
"""
html = replace_once(html, "<script>\n/* ====", shim + "<script>\n/* ====", "start of the main <script>") \
    if html.count("<script>\n/* ====") == 1 else html.replace("<script src=\"vendor/supabase.js\"></script>",
                                                              "<script src=\"vendor/supabase.js\"></script>\n" + shim, 1)

OUT.write_text(html, encoding="utf-8")
print(f"OK: wrote {OUT.relative_to(ROOT)} ({len(html):,} characters)")

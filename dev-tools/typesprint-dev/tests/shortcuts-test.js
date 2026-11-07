const { JSDOM, VirtualConsole } = require("jsdom");
const html = require("fs").readFileSync(process.env.TS_HTML || require("path").join(__dirname, "..", "..", "typesprint", "index.html"), "utf8");
const errs = []; const vc = new VirtualConsole(); vc.on("jsdomError", (e) => { const m = String(e.detail || e.message); if (!/scrollTo/.test(m)) errs.push(m); });
const copied = [], downloads = []; let lastBlob = null, clipboardOk = true;
function open(ls = {}) {
  return new JSDOM(html, { runScripts: "dangerously", pretendToBeVisual: true, url: "http://localhost/", virtualConsole: vc,
    beforeParse(w) {
      w.matchMedia = () => ({ matches: false, addEventListener() {} }); w.scrollTo = () => {}; w.Math.random = () => 0; w.confirm = () => true;
      w.HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
      w.HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); this.dispatchEvent(new w.Event("close")); };
      w.Blob = class { constructor(p) { this.text = p.join(""); } }; w.URL.createObjectURL = (b) => { lastBlob = b; return "blob:t"; }; w.URL.revokeObjectURL = () => {};
      w.HTMLAnchorElement.prototype.click = function () { if (this.download) downloads.push({ name: this.download, text: lastBlob.text }); };
      Object.defineProperty(w.navigator, "clipboard", { value: { writeText: async (t) => { if (!clipboardOk) throw new Error("blocked"); copied.push(t); } } });
      w.fetch = async () => ({ ok: true, json: async () => [] }); w.sessionStorage.setItem("ts-guest", "1");
      Object.entries(ls).forEach(([k, v]) => w.localStorage.setItem(k, v));
    } }).window;
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
(async () => {
  // ---- 1. default colour theme
  let w = open(), d = w.document, $ = (s) => d.querySelector(s), $$ = (s) => [...d.querySelectorAll(s)]; await sleep(120);
  console.log("1. nothing saved -> palette:", d.documentElement.dataset.palette, "| theme:", d.documentElement.dataset.theme);
  $("#palette-btn").click(); console.log("   menu order:", $$(".pal").map((b) => b.textContent).join(", "), "| selected:", $(".pal[aria-pressed=true]").textContent);
  w = open({ "ts-palette": "blue" }); await sleep(100); console.log("   saved Blue is still respected:", w.document.documentElement.dataset.palette);
  // ---- 2. learning progress on My runs (old save format + new format)
  const now = Date.now();
  w = open({ "ts-lessons": JSON.stringify({ home: { acc: 92, secs: 40, at: now }, reach: { done: false, best: 70, last: 70, secs: null, attempts: 2, at: now } }) }); d = w.document; $ = (s) => d.querySelector(s); $$ = (s) => [...d.querySelectorAll(s)]; await sleep(120);
  w.location.hash = "#history"; await sleep(60);
  console.log("2. progress:", $("#lp-count").textContent, "| bar:", $("#lp-bar").style.width, "| rows:", $$("#lp-list li").length);
  console.log("   ", $$("#lp-list li").map((l) => l.textContent.replace(/\s+/g, " ").replace(/\d+\/\d+\/\d+|\d+\.\d+\.\d+/g, "<date>").trim()).join("\n    "));
  console.log("   buttons:", $$("#lp-list button").map((b) => b.textContent).join("/"), "| ticks:", $$("#lp-list .ln.tick").length);
  $$("#lp-list button")[2].click(); await sleep(50); console.log("   Start on lesson 3 ->", w.location.hash, $("#ls-title").textContent);
  // ---- 3. finish "reach" in the UI: attempts go up, best/done update
  w.location.hash = "#learn"; await sleep(40); console.log("3. learn card for reach:", $$(".lesson-card")[1].querySelector(".check").textContent, "| home card:", $$(".lesson-card")[0].querySelector(".check").textContent);
  $$(".lesson-card")[1].click(); await sleep(40); $("#ls-start").click();
  const key = (k) => d.dispatchEvent(new w.KeyboardEvent("keydown", { key: k, bubbles: true }));
  for (let g = 0; g < 600; g++) { const cap = $("#ls-caption").textContent; if (cap.startsWith("Lesson complete") || cap.includes("need 85%")) break; const t = $$("#ls-prompt .ls-ch"), c = t.findIndex((x) => x.classList.contains("cur")); if (c < 0) { await sleep(30); continue; } key(t[c].textContent.toLowerCase()); await sleep(c === t.length - 1 ? 260 : 4); }
  const st = JSON.parse(w.localStorage.getItem("ts-lessons")); console.log("   after finishing:", $("#ls-caption").textContent.slice(0, 40), "| saved reach:", JSON.stringify({ ...st.reach, at: "…" }), "| home untouched:", JSON.stringify(st.home).slice(0, 40));
  w.location.hash = "#history"; await sleep(60); console.log("   My runs now:", $("#lp-count").textContent, "| bar:", $("#lp-bar").style.width);
  $("#h-progress").click(); const pr = downloads.at(-1).text; console.log("   progress report has lessons table:", pr.includes("## Touch-typing lessons") && pr.includes("The home row | completed"), "| reach row:", (pr.match(/Index reaches[^\n]*/) || [""])[0]);
  $("#h-all").click(); const all = JSON.parse(downloads.at(-1).text); console.log("   all-runs json has lessons:", Object.keys(all.lessons).join(","));
  // ---- 4. AI shortcuts
  console.log("4. AI shortcut groups:", $$(".ai-links").length, "| links per group:", $$(".ai-links")[0].children.length, "|", $$(".ai-links")[0].children.length && [...$$(".ai-links")[0].children].map((a) => a.textContent + "→" + new URL(a.href).host).join(", "));
  const anchors = $$("a.ai"); console.log("   open in new tab safely:", anchors.every((a) => a.target === "_blank" && /noopener/.test(a.rel)));
  d.addEventListener("click", (e) => { if (e.target.closest && e.target.closest("a.ai")) e.preventDefault(); });   // stop jsdom trying to navigate
  const claude = $$("#view-history a.ai").find((a) => a.dataset.name === "Claude"); claude.dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true })); await sleep(30);
  console.log("   Claude (history) copied progress report:", copied.at(-1).startsWith("# TypeSprint progress report"), "| note:", $("#ai-note-progress").textContent);
  clipboardOk = false; $$("#view-history a.ai").find((a) => a.dataset.name === "Perplexity").dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true })); await sleep(30); console.log("   clipboard blocked -> note:", $("#ai-note-progress").textContent); clipboardOk = true;
  // results card: win Wordle in one guess, then use the shortcut there
  w.location.hash = "#wordle"; await sleep(40);
  const WORDS = html.match(/const WORDLE_WORDS = \(([\s\S]*?)\)\.split/)[1].replace(/"\s*\+\s*"/g, "").replace(/^\s*"|"\s*$/g, "").replace(/\n\s*/g, "").split(" ");
  for (const c of WORDS.filter((x) => x.length === 5)[0]) key(c); key("Enter"); await sleep(5 * 280 + 400 + 5 * 100 + 1100);
  $$("#results a.ai").find((a) => a.dataset.name === "ChatGPT").dispatchEvent(new w.MouseEvent("click", { bubbles: true, cancelable: true })); await sleep(30);
  console.log("   ChatGPT (results card) copied the run report:", copied.at(-1).startsWith("# TypeSprint report: Wordle"), "| note:", $("#ai-note-run").textContent);
  console.log("ERRORS:", errs.length ? errs : "none"); process.exit(0);
})();

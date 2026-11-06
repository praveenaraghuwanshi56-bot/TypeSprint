# TypeSprint: full project handoff

A cozy, modern typing-practice website: typing tests, seven small games, touch-typing lessons, accounts with a leaderboard, and
downloadable run logs that can be given to an AI coach. This document explains **everything built so far** so you can start a new
chat (or hand the project to another AI) and continue exactly where this one stopped.

* **Deliverables:** `index.html` (the whole website, one file), `supabase-setup.sql` (the database), this `README.md`,
  `my-tests.txt` (sample texts in the upload format), and `typesprint-dev-tools.zip` (test scripts, not part of the site).
* **Hosting:** Cloudflare Pages (direct upload: drag a folder containing `index.html`). Earlier it was Netlify; nothing depends on the host.
* **Backend:** Supabase (Postgres). The site talks to it only through database functions (RPC). Supabase URL and anon key are in two constants at the top of the script in `index.html`.
* **Owner:** a non-technical person who deploys by drag-and-drop and prefers one-file deployments, simple steps, and a cozy look. Their favourite colour theme is **Sunset** (the default).

---

## 1. Paste this into a new chat to continue

> I am continuing a project called TypeSprint. The attached README.md explains the whole project. The site is ONE file, `index.html`
> (HTML + CSS + JavaScript inline, no build step), plus `supabase-setup.sql`. Please read the README first, then the comments at
> the top of the script ("HOW THIS SCRIPT IS ORGANISED"). Rules: keep it a single deployable `index.html`; edit with exact string
> replacements and assert each one matched; run the dev-tools tests after every change; if you change the database, update
> `supabase-setup.sql` (safe to re-run) and tell me to run it again; explain deploy steps simply; be honest about what you could not test.
> Here is what I want next: ...

Attach: `index.html`, `supabase-setup.sql`, `README.md`, and optionally `typesprint-dev-tools.zip`.

---

## 2. How the site is built

### One file, many pages
`index.html` contains, in order: the sign-in gate, the header, one `<section id="view-...">` per page, the results `<dialog>`,
the floating "My runs" button, then `<style>` (all CSS) and one `<script>` (all JavaScript, wrapped in one function).
There are **no hash-path routes with slashes**; routes are plain hashes and the router shows exactly one section at a time.

| Route | Page |
|---|---|
| `#home` | Home cards (Typing practice, Games, Learn) |
| `#practice` | Opens `#classic` or `#timed` (remembers the last one) |
| `#classic`, `#timed` | Typing tests (share one section, `view-type`, which also holds the Reading nook side panel) |
| `#games` | Games hub |
| `#balloons`, `#wordle`, `#scramble`, `#emoji`, `#blink`, `#cafe`, `#gap` | The seven games |
| `#learn`, `#lesson` | Learn hub; one lesson (which lesson is held in memory in `lessonId`) |
| `#leaderboard` | Rankings |
| `#history` | "My runs": learning progress, AI shortcuts, downloads, recent runs |
| `#upload` | Admin-only text upload (non-admins are redirected to `#home`) |

### Script sections (in file order)
1 Database helpers (`rpc`, `saveResult`) - 2 small helpers (`$`, `$$`, `esc`, `shuffle`, `pick`, `RUN`/`lg` event log) - 3 word pool (built-in + Datamuse) -
4 appearance (light/dark/system, colour themes) - 5 text library and the Reading nook list - 6 router - 7 typing practice (+ Wikipedia source) -
8 games - 9 Reading nook open/close - 10 accounts and account menu - 11 leaderboard - 12 run logs, AI reports, history, AI shortcuts -
13 Learn (Beginners/Advanced courses, lessons, tips, rhythm trainer) - 14 results card `showResults()` - 15 keyboard shortcut - 16 admin upload - 17 mobile helpers (device detection, native keyboard focus, Type button) - 18 start-up.
Every top-level function and variable has a one-line comment above it.

### The pattern every mode follows
* A state object (`T`, `G`, `B`, `C`, `GP`, `W`, `LS`), `start*/stop*/end*` functions, and (for games) a `requestAnimationFrame` or timer loop.
* The mode logs events with `lg(kind, ...data)` into `RUN.events` (timestamps are ms since the run began). `beginRun()` resets it.
* It finishes by calling **`showResults({ mode, variant, label, wpm, accuracy, errors, duration_seconds, score?, best_streak?, extra?, rating?, cells?, scale? })`**.
  `showResults` shows the card, calls `recordRun()` (history + AI report data) and, if signed in, `saveResult()` (leaderboard).
  `scale` multiplies WPM before choosing the rating (waiting time lowers raw speed in games); `rating` and `cells` override the default WPM rating/cells (Wordle uses them).

### Browser storage (nothing here leaves the browser unless noted)
| Key | Where | Holds |
|---|---|---|
| `ts-theme` | localStorage | `light` or `dark`; absent = follow the browser |
| `ts-palette` | localStorage | colour theme id; absent = `sunset` |
| `ts-session` | localStorage | `{token, username, is_admin, letter, color}` (the signed-in player) |
| `ts-guest` | sessionStorage | `1` when "Continue as guest" was chosen this visit |
| `ts-nook` | localStorage | `open` / `closed` (Reading nook side panel) |
| `ts-runs` | localStorage | last 40 finished runs with logs and analysis |
| `ts-lessons` | localStorage | `{lessonId: {done, best, last, secs, attempts, at}}` (older saves `{acc, secs, at}` are understood) |
| `ts-wordle` | localStorage | Wordle streaks per word length |
| `ts-wiki-titles`, `ts-words` | localStorage | cached Wikipedia title list and Datamuse word pool (7 days) |

Because storage is per browser *and per web address*, moving hosts or domains starts everyone fresh locally (accounts and the leaderboard live in Supabase and are unaffected).

---

## 3. Features, in detail

### Typing practice (`#practice`)
* **Classic**: type a passage start to finish. **Timed**: 15/30/60/120 s; texts are chained to fill the time.
* Live WPM, accuracy, errors, time. Correct letters sage-green, mistakes coral, amber glowing cursor. `Tab` then `Enter` restarts any mode.
* **Reading nook** (left side panel, slides in/out with the sidebar icon on the panel / next to the options; remembers its state; becomes a drawer on phones): "Surprise me", "Wikipedia", every text, difficulty filter (All/Easy/Medium/Hard), and (admin only) "Add your own texts".
* **Wikipedia source**: random paragraphs from ~1,000 "vital article" titles (the list is fetched from Wikipedia's Level 3 vital-articles page and cached; 30 built-in titles are the fallback). Text is cleaned to plain typable ASCII; attribution (CC BY-SA 4.0) is shown under the text. Falls back to saved texts if offline.
* Rating by WPM: under 15 Warming Up, 30 Cozy Pace, 50 Steady Hands, 70 Speedster, above Lightning Fingers (+ a hint to slow down if accuracy < 90%).

### Games (`#games`)
The games hub lists **Balloons** and **Wordle** first, then the newer games, then the older ones. Balloons, Blink, Cafe and Fill the gap ease in gently (about 3 minutes to full pace) and cap at a fair maximum. Word Scramble and Emoji Rush use a shorter per-round timer instead.
* **Balloons**: words or letters A-Z float up; type a balloon before it escapes; 3 lives. Words mode: crossing time 14 s -> 8 s, spawn gap 2.6 s -> 1.5 s, word length 4 -> 8, and the pool widens from common to rarer words. Letters mode: 12 s -> 7 s, 1.7 s -> 0.85 s. Words come from Datamuse themed lists (`WORD_THEMES` constant near the top; default cozy, garden, kitchen, weather, forest, tea, animals, music) with a built-in fallback and a small profanity filter.
* **Wordle**: 4, 5 or 6 letters; 6 guesses; flip, shake and bounce animations; on-screen + physical keyboard; repeated letters scored correctly; guesses accepted if they are in the answer list, in the word pool or confirmed by Datamuse (offline: accepted). Answer list is curated: 101 four-, 145 five-, 92 six-letter words (`WORDLE_WORDS`). Streaks per length are stored locally.
* **Word Scramble**: a word's letters are shuffled; type the unscrambled word before the round timer empties. Words grow from 4 to 8 letters and the timer shrinks from 18 s to 8 s. 3 lives; a correct answer earns a time bonus and a streak bonus. Uses the built-in word list.
* **Emoji Rush**: an emoji appears; type its name before the timer empties. The timer shrinks from 15 s to 6 s. 3 lives; a correct answer earns a time bonus and a streak bonus. Names are deduplicated so there is no ambiguity.
* **Blink words**: a word shows briefly, then hides; type it from memory. Show time 2.6 s -> 1.1 s, length 4 -> 8 letters (grows every 4 words), 3 lives.
* **Tea Time Cafe**: customers (animal faces) arrive with orders (`latte` -> `two scones` -> `a mocha and an apple pie`); type the order, spaces included, before the patience bar empties; tips for speed; 3 lives; orders showing at once start with different letters so the first key picks the customer.
* **Fill the gap**: a Wikipedia sentence (8-20 words) with one word blanked; **one random letter (two for 8+ letter words) is pre-filled in amber**; type the whole word; blank length 5 -> 8 letters over 30 sentences; **5 lives**; no hint button. Falls back to the player's texts if offline.

### Accounts, guests, leaderboard
* **Custom accounts built on database functions** (not Supabase Auth): username (3-16 of `a-z 0-9 _`) + password (6-72 chars), **no email**, so there is no password recovery (the owner resets passwords in the SQL editor).
* **Stay signed in** via a token in `localStorage`; the page verifies it on start, every 30 s and when the tab regains focus.
* **One device at a time**: signing in anywhere replaces the stored session hash, so the previous device is signed out within about 30 s ("You were signed out because this account was signed in on another device").
* **Guest** button: play everything, but nothing is saved and guests never appear on the leaderboard. The sign-in screen returns on each new visit.
* **Admin** account (`admin`) is created by `supabase-setup.sql` (section 9; the starting password is set there, change it with the command at the bottom of that file). The admin sees "Add tests" links; the server enforces admin-only uploads. The admin account cannot be deleted from the UI.
* **Account menu** (click the round avatar): rename, change icon (one letter or emoji + background colour from 10 swatches or any colour; text colour auto-contrasts), sign out, delete account (needs password; removes scores), My runs. Guests get Sign in / Create account / My runs.
* **Leaderboard**: 12 boards (Classic WPM, Timed WPM, Balloons words/letters score, Blink, Cafe, Fill the gap, Word Scramble, Emoji Rush, Wordle 4/5/6 best streak), best result per player, WPM boards need >= 90% accuracy, avatars shown, your row highlighted, styled dropdown with groups.

### Appearance
* Light / dark / **System** (default: follows the browser; the choice is applied before first paint so there is no flash).
* **Colour themes** (palette button in the header): **Sunset (default)**, Cozy, Blue, Cyan, Forest, Violet, Rose, Slate; each has a light and a dark version. All were contrast-checked (text, muted text, accent text, tile text, balloon text).

### Mobile & touch
* **Auto-detection**: the head script checks `pointer: coarse`, `hover: none`, `navigator.maxTouchPoints` and the user agent, then sets `data-mobile="true"` on `<html>` before first paint. The main script re-checks on resize and on pointer/hover changes.
* **Native keyboard**: on a phone or tablet, a floating **Type** button (bottom-right) opens the native keyboard for Classic/Timed, Balloons, Blink, Tea Time Cafe, Fill the gap, Word Scramble and Emoji Rush. Tapping the game area also focuses the hidden input.
* **Wordle & lessons**: both keep their on-screen keyboards and add a **⌨ Use my keyboard** button on mobile, which focuses a hidden input wired to the game.
* **Mobile-friendly inputs**: hidden inputs are fixed/centred, 16px, with `inputmode="text"` and `enterkeyhint="done"`; the viewport uses `viewport-fit=cover`; the Balloons arena uses `dvh`; the focus hint says "Tap here to type".
* **Fallback**: if the native keyboard does not open (some in-app browsers), the on-screen keyboards for Wordle and lessons still work, and tapping the game area or the Type button retries the native keyboard.

### Run logs and AI evaluation
* Every run is logged (`RUN.events`). Classic/Timed log every keystroke and backspace; games log their own events (balloon spawn/pop/escape/wrong key; cafe arrive/serve/leave/wrong key; blink word/answer; gap question/answer; wordle guess; scramble round/answer/timeout; emoji round/answer/timeout).
* **Results card buttons**: *Report for AI* (`.md`, with coaching instructions for the AI and computed tables), *Raw log* (`.json`), *Copy for AI*, and **AI shortcut buttons** (Claude, ChatGPT, Gemini, Copilot, Perplexity): clicking copies the report to the clipboard and opens that site in a new tab; paste into the chat. Nothing is sent automatically.
* Typing analysis (`analyzeTyping`): raw vs net WPM, backspaces, mean/SD of key gaps and consistency, pauses > 1 s, WPM per 5 s, slowest keys, most-missed keys, expected->typed mix-ups, error rate and speed per finger (standard QWERTY map) and per keyboard row.
* **My runs** (`#history`, floating rounded button bottom-left, also in the account menu): *Learning progress* (lessons completed, best accuracy, attempts), AI shortcuts for the **progress report** (trend, persistent weak keys/fingers, lessons), downloads (progress report, all runs `.json` including lessons, per-run report/log), recent runs (last 40, browser only), clear history.
* The results card also shows one personalised tip (e.g. low accuracy -> "Accuracy comes first").

### Learn (`#learn`)
* **Two courses, 10 interactive lessons**: the **Beginners** course (home row, G/H reaches, top row, bottom row, everything together) and an **Advanced** course (number row, punctuation, tricky words, flow sentences, speed & stamina). The Learn page has a tab per course. Advanced unlocks once every Beginners lesson is completed with 85% accuracy or better; the **admin account can open any course regardless of progress**. Each lesson shows an on-screen QWERTY keyboard coloured by finger (with the bumps on F and J), a number row, and two animated hands. "Watch the demo" lights each key, raises the right finger and taps it with captions; "Start practice" runs single keys, 3-letter chunks and real words; wrong keys shake the prompt; a progress bar tracks the lesson and a confetti burst celebrates a pass; **85% accuracy completes a lesson**; progress is saved (`ts-lessons`) with attempts and best accuracy. Finishing the last Beginners lesson offers a shortcut straight into Advanced.
* **Tips**: 10 animated cards + tip of the day. **Rhythm trainer**: pulsing circle at 60/80/100/120 BPM; tap Space on the beat; 16 taps then average offset from the beat.

### Admin upload (`#upload`, admin only)
Paste text or choose a `.txt`; format per text: header lines `title:`, `difficulty: easy|medium|hard`, `category:`, then a line `---`, then the text on one line; texts separated by a line `===`. A plain paragraph also works. Text is normalised to ASCII (40-3000 chars). `AI_PROMPT` (copy button on the page) is a prompt that makes an AI write texts in this format. The page lists uploaded texts with Delete.

**App file**: the admin can also upload a single file (e.g. the Windows app) in the "App file" section. Uploading replaces the previous file (only one is stored at a time, so space isn't wasted). Users can download it from the **"Download"** button in the top-right header, next to the light/dark mode toggle. The file is served from Supabase storage (bucket `app_files`).

---

## 4. Database (`supabase-setup.sql`, safe to re-run, run it in Supabase -> SQL Editor)
* **Tables**: `results` (player_id, mode, variant, wpm, accuracy, errors, duration_seconds, score, best_streak), `custom_tests`, `players` (username, bcrypt `pass_hash`, `is_admin`, `session_hash`, lockout fields, `avatar_letter`, `avatar_color`).
* **Security model**: row-level security on every table; the browser role has **no** direct table access except `select` on `custom_tests`; everything else is a `security definer` function. Session tokens are random and stored only as sha256 hashes. 5 wrong passwords lock an account for 15 minutes (login and delete). The anon key in `index.html` is public by design.
* **Functions**: `signup, login, check_session, logout, save_result, leaderboard, rename_account, set_avatar, delete_account, add_tests, delete_test` (+ internal `_hash_tok, _new_token, _uid`). They return `{"ok":true,...}` or `{"ok":false,"error":"code"}`; codes are mapped to friendly text in the `ERRORS` constant in the script.
* `results.mode` is checked against: `typing, timed, balloons, blink, cafe, gap, wordle`. **Adding a game means adding its mode to that check** (and re-running the SQL).
* **Storage**: the `app_files` public bucket holds the downloadable app file (object path `TypeSprint-App`). It is created by `supabase-setup.sql` with public read and authenticated write policies. Only one object exists at a time — uploading replaces the previous file.

---

## 5. Deploying and operating
1. Supabase: SQL Editor -> paste all of `supabase-setup.sql` -> Run. Put the project URL and anon key in the two constants at the top of the script in `index.html` (already done for the owner's project).
2. Cloudflare Pages: Workers & Pages -> the project -> *Create new deployment* -> drag a **folder containing `index.html`** (or a zip) -> Deploy. Git-connected projects: push instead. Hard-refresh (Ctrl+Shift+R) afterwards.
3. After every update that changes `supabase-setup.sql`, run it again in Supabase.
4. Change the admin password / remove a player: see the comments at the bottom of `supabase-setup.sql`.
5. If the page ever looks unstyled or dead on a custom domain, check that Cloudflare Rocket Loader is off.

## 6. Recipes for common changes
* **Change the default colour theme**: head script `p||'sunset'` and `root.dataset.palette || "sunset"` in `renderThemeMenu`, and the order of the `PALETTES` array.
* **Add a colour theme**: add a light rule `:root[data-palette="id"]{...}` and a dark rule `:root[data-palette="id"][data-theme="dark"]{...}` at the end of `<style>` with the same 20 variables (copy an existing pair), and an entry in `PALETTES`. Check contrast (text/background >= 7, accent text >= 4.5).
* **Add an AI shortcut**: add an entry to `AIS`.
* **Add a lesson**: add an object to `LESSONS` with a `course` (`"beginners"` or `"advanced"`), `keys`, `focus`, `tip` and `words`; the Learn tabs, My runs and reports pick it up. Add a new course by adding an entry to `COURSES` (with `requires` naming its prerequisite, or `null`) and giving its lessons that course id.
* **Tune difficulty**: Balloons `PACE` and the length formula in `spawn` calls; Blink `nextWord`; Cafe `makeOrder`, `seatCustomer`, `tickCafe`; Gap `gapNext`; the 180000 ms (3 minutes) ramp lengths.
* **Add a game**: new `<section id="view-x">`, a card in `view-games`, add to `GAMES`/`ROUTES`/the `view` map in `route()`, state + start/stop/end functions, `lg()` events, `showResults()` at the end, a section in `gameSections()`, a leaderboard entry in `BOARDS`, the mode in the SQL check, and add it to `restart()` and the stop calls in `route()`.
* **Add leaderboard boards**: `BOARDS` (mode, optional variant, metric `wpm|score|best_streak`).
* **Add a word theme for Balloons/Blink**: edit `WORD_THEMES` at the top of the script.

---

## 7. How it was tested, and what was not
* **Page behaviour**: jsdom (a pretend browser) with a fake Supabase that follows the SQL rules: sign-in gate, guest, sign up, persistence, other-device sign-out, admin-only upload, account menu, leaderboard, themes, typing log/report/downloads, games (including Word Scramble and Emoji Rush), lessons, rhythm trainer, AI shortcuts. See `typesprint-dev-tools.zip` (`npm test`).
* **Mobile/touch**: a simulated touch browser (coarse pointer, no hover, mobile user agent) checked the auto-detection, the floating Type button, the Wordle/lesson device-keyboard buttons, typing through the hidden inputs, and the Type button hiding when the results dialog opens.
* **Database**: the SQL was run on a real Postgres (the `pgserver` package) with a stand-in for the password-hashing functions (real Supabase has genuine pgcrypto): accounts, one-session rule, lockout, rename/icon/delete, scores, leaderboard, admin-only functions, and "browser cannot read tables" (`npm run test:sql`).
* **CSS**: parsed with css-tree (no syntax problems); all colour themes checked to define the same variables; contrast ratios computed.
* **Not tested**: how it *looks* on real screens (layout, animations, colours, phones, the fixed sidebar and bottom-left button), live Wikipedia and Datamuse responses, the real Supabase project, Cloudflare Pages itself. Treat these as "please check by eye" after each deploy.
* **A past bug worth knowing**: during the move to a single file, a typo (`!!`) made the site skip saving results whenever Supabase keys were set. It was fixed when accounts were added. Lesson: tests that run without keys can hide bugs that only appear with keys.

## 8. Known limits and leftovers
* Scores are computed in the browser, so a determined cheater can post fake scores (the database only rejects impossible values such as WPM > 400). Sign-ups are open (no rate limit); no email, so no password recovery.
* History, lessons, streaks and theme are per browser/address. Lessons assume a QWERTY keyboard. The Wordle answer list is small (338 words). Mobile keyboard behaviour varies by browser; the on-screen keyboards are the fallback.
* Unused leftovers (safe to delete): `playerId`, `wordsUpTo`, CSS for `.pick`, `select` and `#pin-input`. `my-tests.txt` is only a sample of the upload format.
* Ideas not built: daily Wordle, syncing history/lessons to Supabase, sound effects, more languages/keyboard layouts, more lessons (shifted symbols, capitals), password reset by email, leaderboards by week.

## 9. Project history (what was built, in order)
1. **Prototype**: static site with a typing test, Balloons, results card, light/dark toggle, Supabase config + results table, Netlify deploy steps.
2. **More modes**: home page, Timed test, Blink words, a folder of `.txt` texts with a build script and an AI prompt template, Balloons letters mode with a gentle difficulty ramp, new icon.
3. **Single-file rewrite**: downloaded files had landed in one folder and broke the page, so everything moved into one `index.html`; texts were uploaded through the site with a 4-digit PIN (later replaced by accounts).
4. **Sources**: Wikipedia mode (Classic/Timed), Datamuse words for games, styled Reading nook side panel.
5. **Games and structure**: Tea Time Cafe, Fill the gap (later made easier: clue letter, 5 lives, shorter), Wordle (4-6 letters), Practice and Games tabs.
6. **Accounts**: custom sign-up/sign-in, guest mode, one device at a time, leaderboard, admin-only upload, left slide-in sidebar.
7. **Polish**: account menu (rename/icon/delete), styled dropdowns, sidebar icon, hosting moved from Netlify to Cloudflare Pages.
8. **Learning and evaluation**: run logs and AI reports, My runs, Learn tab (lessons, tips, rhythm trainer).
9. **Courses**: the Learn tab grew Beginners and Advanced course tabs, five new advanced lessons (number row, punctuation, tricky words, flow, speed), a lock/progress panel for Advanced, admin access to every course, and extra lesson animations (progress bar, confetti, staggered cards, key-press feedback).
10. **Themes**: eight colour themes, Sunset made the default, floating My runs button, lesson progress on My runs, AI shortcut buttons.
11. **Documentation**: code comments throughout `index.html` and `supabase-setup.sql`, this README, and the dev-tools test bundle.
12. **More games**: added **Word Scramble** and **Emoji Rush** with per-round timers, score/streak/lives, AI reports and leaderboard boards; reordered the games hub so **Balloons** and **Wordle** come first; extended the SQL mode check to the two new modes.
13. **Mobile & touch**: auto-detection of touch/mobile devices, a floating Type button that opens the native keyboard in every typing mode, "Use my keyboard" buttons for Wordle and lessons, mobile-friendly hidden inputs, and touch/layout tweaks.

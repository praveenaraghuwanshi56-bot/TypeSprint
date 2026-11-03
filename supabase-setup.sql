-- =====================================================================================
-- OVERVIEW (read this first)
-- Tables   : results (one row per finished run), custom_tests (texts uploaded by the admin),
--            players (accounts; the browser can never read this table).
-- Security : row-level security is on everywhere. The browser (anon key) can ONLY call the
--            functions below, plus read custom_tests. Passwords are bcrypt-hashed; session
--            tokens are stored as sha256 hashes. Wrong passwords: 5 tries, then 15 minutes locked.
-- Functions (all return jsonb like {"ok":true,...} or {"ok":false,"error":"code"}):
--   signup, login, check_session, logout        accounts; login REPLACES the stored session, which
--                                               signs the account out on every other device
--   save_result, leaderboard                    scores; WPM boards only count runs with >= 90% accuracy
--   rename_account, set_avatar, delete_account  account settings (delete needs the password; admin protected)
--   add_tests, delete_test                      admin only
--   _hash_tok, _new_token, _uid                 internal helpers, not callable from the browser
-- The admin account ("admin") is created in section 9 at the bottom. Change its password there.
-- =====================================================================================
-- TypeSprint database setup. Run this whole file ONCE in Supabase → SQL Editor. Safe to run again.
-- It replaces the old PIN system with accounts: players sign up and sign in, only one device
-- per account stays signed in, scores feed a leaderboard, and only the admin can add texts.

create extension if not exists pgcrypto with schema extensions;

-- 1) Saved results ---------------------------------------------------------
create table if not exists public.results (
  id               uuid primary key default gen_random_uuid(),
  created_at       timestamptz not null default now(),
  player_id        uuid not null,                       -- the signed-in player's id
  mode             text not null,
  variant          text,
  wpm              numeric(5,1) not null check (wpm between 0 and 400),
  accuracy         numeric(4,1) not null check (accuracy between 0 and 100),
  errors           integer      not null check (errors >= 0),
  duration_seconds numeric(7,1) not null check (duration_seconds >= 0),
  score            integer check (score >= 0),
  best_streak      integer check (best_streak >= 0)
);
alter table public.results add column if not exists variant text;
alter table public.results drop constraint if exists results_mode_check;
alter table public.results add constraint results_mode_check
  check (mode in ('typing','timed','balloons','blink','cafe','gap','wordle','scramble','emoji'));
create index if not exists results_board_idx on public.results (mode, variant);
alter table public.results enable row level security;
drop policy if exists "anyone can save a result" on public.results;   -- results now go through save_result() only
revoke all on public.results from anon, authenticated;

-- 2) Uploaded typing texts: everyone can read, only the admin can write -----
create table if not exists public.custom_tests (
  id         uuid primary key default gen_random_uuid(),
  created_at timestamptz not null default now(),
  title      text not null check (char_length(title) between 1 and 80),
  difficulty text not null default 'medium' check (difficulty in ('easy','medium','hard')),
  category   text not null default 'general' check (char_length(category) <= 30),
  text       text not null check (char_length(text) between 40 and 3000)
);
alter table public.custom_tests enable row level security;
drop policy if exists "anyone can read tests" on public.custom_tests;
create policy "anyone can read tests" on public.custom_tests for select to anon, authenticated using (true);
revoke all on public.custom_tests from anon, authenticated;
grant select on public.custom_tests to anon, authenticated;

-- 3) Players. No policies at all, so the browser can never read this table ----
create table if not exists public.players (
  id              uuid primary key default gen_random_uuid(),
  username        text not null unique check (username ~ '^[a-z0-9_]{3,16}$'),
  pass_hash       text not null,                         -- bcrypt, never the password itself
  is_admin        boolean not null default false,
  session_hash    text,                                  -- hash of the ONE active session token
  failed_attempts int not null default 0,
  locked_until    timestamptz,
  created_at      timestamptz not null default now()
);
alter table public.players add column if not exists avatar_letter text;   -- one character shown in the account icon
alter table public.players add column if not exists avatar_color text;    -- #rrggbb icon background
alter table public.players enable row level security;
revoke all on public.players from anon, authenticated;

-- 4) Remove the old PIN system ------------------------------------------------
drop function if exists public.verify_pin(text);
drop function if exists public.add_tests(text, jsonb);
drop function if exists public.delete_test(text, uuid);
drop function if exists public._check_pin(text);
drop table if exists public.upload_settings;

-- 5) Helpers (not callable from the browser) ---------------------------------
create or replace function public._hash_tok(t text) returns text
language sql immutable as $$ select encode(sha256(convert_to(coalesce(t, ''), 'utf8')), 'hex') $$;

create or replace function public._new_token() returns text
language sql as $$ select replace(gen_random_uuid()::text || gen_random_uuid()::text, '-', '') $$;

create or replace function public._uid(tok text) returns uuid
language sql stable security definer set search_path = public as $$
  select id from public.players where session_hash is not null and session_hash = public._hash_tok(tok) limit 1
$$;
revoke all on function public._hash_tok(text), public._new_token(), public._uid(text) from public, anon, authenticated;

-- 6) Sign up / sign in / sign out ----------------------------------------------
create or replace function public.signup(uname text, pw text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare u text := lower(btrim(coalesce(uname, ''))); tok text;
begin
  if u !~ '^[a-z0-9_]{3,16}$' then return jsonb_build_object('ok', false, 'error', 'bad_username'); end if;
  if u in ('admin','administrator','root','moderator','typesprint') then return jsonb_build_object('ok', false, 'error', 'taken'); end if;
  if char_length(coalesce(pw, '')) < 6 or char_length(pw) > 72 then return jsonb_build_object('ok', false, 'error', 'bad_password'); end if;
  tok := public._new_token();
  begin
    insert into public.players (username, pass_hash, session_hash)
    values (u, extensions.crypt(pw, extensions.gen_salt('bf')), public._hash_tok(tok));
  exception when unique_violation then
    return jsonb_build_object('ok', false, 'error', 'taken');
  end;
  return jsonb_build_object('ok', true, 'token', tok, 'username', u, 'is_admin', false, 'avatar_letter', null, 'avatar_color', null);
end $$;

-- Signing in replaces the stored session, which signs the account out everywhere else.
create or replace function public.login(uname text, pw text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare p public.players%rowtype; tok text;
begin
  select * into p from public.players where username = lower(btrim(coalesce(uname, ''))) for update;
  if not found then return jsonb_build_object('ok', false, 'error', 'wrong'); end if;
  if p.locked_until is not null and p.locked_until > now() then return jsonb_build_object('ok', false, 'error', 'locked'); end if;
  if p.pass_hash = extensions.crypt(coalesce(pw, ''), p.pass_hash) then
    tok := public._new_token();
    update public.players set session_hash = public._hash_tok(tok), failed_attempts = 0, locked_until = null where id = p.id;
    return jsonb_build_object('ok', true, 'token', tok, 'username', p.username, 'is_admin', p.is_admin, 'avatar_letter', p.avatar_letter, 'avatar_color', p.avatar_color);
  end if;
  update public.players
     set failed_attempts = case when failed_attempts + 1 >= 5 then 0 else failed_attempts + 1 end,
         locked_until    = case when failed_attempts + 1 >= 5 then now() + interval '15 minutes' end
   where id = p.id;
  return jsonb_build_object('ok', false, 'error', 'wrong');
end $$;

create or replace function public.check_session(tok text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare p public.players%rowtype;
begin
  select * into p from public.players where session_hash is not null and session_hash = public._hash_tok(tok) limit 1;
  if not found then return jsonb_build_object('ok', false, 'error', 'not_signed_in'); end if;
  return jsonb_build_object('ok', true, 'username', p.username, 'is_admin', p.is_admin, 'avatar_letter', p.avatar_letter, 'avatar_color', p.avatar_color);
end $$;

create or replace function public.logout(tok text) returns jsonb
language plpgsql security definer set search_path = public as $$
begin
  update public.players set session_hash = null where session_hash is not null and session_hash = public._hash_tok(tok);
  return jsonb_build_object('ok', true);
end $$;

-- 7) Scores and leaderboard ---------------------------------------------------
create or replace function public.save_result(tok text, r jsonb) returns jsonb
language plpgsql security definer set search_path = public as $$
declare uid uuid := public._uid(tok);
begin
  if uid is null then return jsonb_build_object('ok', false, 'error', 'not_signed_in'); end if;
  insert into public.results (player_id, mode, variant, wpm, accuracy, errors, duration_seconds, score, best_streak)
  values (uid, r->>'mode', left(r->>'variant', 60), (r->>'wpm')::numeric, (r->>'accuracy')::numeric, (r->>'errors')::int,
          (r->>'duration_seconds')::numeric, nullif(r->>'score', '')::int, nullif(r->>'best_streak', '')::int);
  return jsonb_build_object('ok', true);
exception when others then
  return jsonb_build_object('ok', false, 'error', 'invalid_result');
end $$;

-- Best result per player. WPM boards only count runs with at least 90% accuracy.
create or replace function public.leaderboard(p_mode text, p_variant text, p_metric text, lim int default 20) returns jsonb
language plpgsql security definer stable set search_path = public as $$
begin
  if p_metric not in ('wpm', 'score', 'best_streak') then return '[]'::jsonb; end if;
  return coalesce((
    select jsonb_agg(jsonb_build_object('rank', x.rk, 'username', x.username, 'value', x.v, 'avatar_letter', x.avatar_letter, 'avatar_color', x.avatar_color) order by x.rk)
    from (
      select row_number() over (order by b.v desc, b.username) as rk, b.username, b.avatar_letter, b.avatar_color, b.v
      from (
        select p.username, p.avatar_letter, p.avatar_color,
               max(case p_metric when 'wpm' then r.wpm when 'score' then r.score when 'best_streak' then r.best_streak end) as v
        from public.results r join public.players p on p.id = r.player_id
        where r.mode = p_mode and (p_variant is null or r.variant = p_variant)
          and (p_metric <> 'wpm' or r.accuracy >= 90)
        group by p.username, p.avatar_letter, p.avatar_color
      ) b
      where b.v is not null and b.v > 0
      order by 1
      limit least(greatest(coalesce(lim, 20), 1), 50)
    ) x
  ), '[]'::jsonb);
end $$;

-- 7b) Account settings: rename, icon, delete ---------------------------------
create or replace function public.rename_account(tok text, new_name text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare uid uuid := public._uid(tok); u text := lower(btrim(coalesce(new_name, ''))); cur text;
begin
  if uid is null then return jsonb_build_object('ok', false, 'error', 'not_signed_in'); end if;
  if u !~ '^[a-z0-9_]{3,16}$' then return jsonb_build_object('ok', false, 'error', 'bad_username'); end if;
  select username into cur from public.players where id = uid;
  if u in ('admin','administrator','root','moderator','typesprint') and u <> cur then
    return jsonb_build_object('ok', false, 'error', 'taken');
  end if;
  begin
    update public.players set username = u where id = uid;
  exception when unique_violation then
    return jsonb_build_object('ok', false, 'error', 'taken');
  end;
  return jsonb_build_object('ok', true, 'username', u);
end $$;

create or replace function public.set_avatar(tok text, letter text, color text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare uid uuid := public._uid(tok); l text := nullif(left(btrim(coalesce(letter, '')), 1), ''); c text := lower(color);
begin
  if uid is null then return jsonb_build_object('ok', false, 'error', 'not_signed_in'); end if;
  if c is not null and c !~ '^#[0-9a-f]{6}$' then return jsonb_build_object('ok', false, 'error', 'bad_color'); end if;
  update public.players set avatar_letter = l, avatar_color = c where id = uid;
  return jsonb_build_object('ok', true, 'avatar_letter', l, 'avatar_color', c);
end $$;

-- Needs the password again. Wrong guesses count toward the same 5-try lockout as signing in.
create or replace function public.delete_account(tok text, pw text) returns jsonb
language plpgsql security definer set search_path = public as $$
declare uid uuid := public._uid(tok); p public.players%rowtype;
begin
  if uid is null then return jsonb_build_object('ok', false, 'error', 'not_signed_in'); end if;
  select * into p from public.players where id = uid for update;
  if p.is_admin then return jsonb_build_object('ok', false, 'error', 'admin_protected'); end if;
  if p.locked_until is not null and p.locked_until > now() then return jsonb_build_object('ok', false, 'error', 'locked'); end if;
  if p.pass_hash <> extensions.crypt(coalesce(pw, ''), p.pass_hash) then
    update public.players
       set failed_attempts = case when failed_attempts + 1 >= 5 then 0 else failed_attempts + 1 end,
           locked_until    = case when failed_attempts + 1 >= 5 then now() + interval '15 minutes' end
     where id = uid;
    return jsonb_build_object('ok', false, 'error', 'wrong');
  end if;
  delete from public.results where player_id = uid;
  delete from public.players where id = uid;
  return jsonb_build_object('ok', true);
end $$;

-- 8) Admin-only text management -------------------------------------------------
create or replace function public.add_tests(tok text, tests jsonb) returns jsonb
language plpgsql security definer set search_path = public as $$
declare uid uuid := public._uid(tok); n int;
begin
  if uid is null or not exists (select 1 from public.players where id = uid and is_admin) then
    return jsonb_build_object('ok', false, 'error', 'forbidden');
  end if;
  if jsonb_typeof(tests) <> 'array' or jsonb_array_length(tests) not between 1 and 50 then
    return jsonb_build_object('ok', false, 'error', 'Send between 1 and 50 texts at a time.');
  end if;
  insert into public.custom_tests (title, difficulty, category, text)
  select left(e.t->>'title', 80), coalesce(nullif(e.t->>'difficulty', ''), 'medium'),
         left(coalesce(nullif(e.t->>'category', ''), 'general'), 30), e.t->>'text'
  from jsonb_array_elements(tests) as e(t);
  get diagnostics n = row_count;
  return jsonb_build_object('ok', true, 'added', n);
end $$;

create or replace function public.delete_test(tok text, test_id uuid) returns jsonb
language plpgsql security definer set search_path = public as $$
declare uid uuid := public._uid(tok);
begin
  if uid is null or not exists (select 1 from public.players where id = uid and is_admin) then
    return jsonb_build_object('ok', false, 'error', 'forbidden');
  end if;
  delete from public.custom_tests where id = test_id;
  return jsonb_build_object('ok', true);
end $$;

grant execute on function
  public.signup(text, text), public.login(text, text), public.check_session(text), public.logout(text),
  public.save_result(text, jsonb), public.leaderboard(text, text, text, int),
  public.add_tests(text, jsonb), public.delete_test(text, uuid),
  public.rename_account(text, text), public.set_avatar(text, text, text), public.delete_account(text, text)
to anon, authenticated;

-- 9) The admin account: username "admin" -----------------------------------------
insert into public.players (username, pass_hash, is_admin)
values ('admin', extensions.crypt('rudsilver56', extensions.gen_salt('bf')), true)
on conflict (username) do nothing;

-- To change the admin password later, run (and put your new password inside the quotes):
--   update public.players set pass_hash = extensions.crypt('NEW PASSWORD', extensions.gen_salt('bf')), session_hash = null
--   where username = 'admin';
-- To remove someone: delete from public.players where username = 'their_name';

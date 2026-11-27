#!/usr/bin/env python3
"""Write glossary definitions for the pending terms with `claude -p` on the owner's subscription (no API key).

Replaces the claude.ai routine "DGG glossary definitions" (Nov 26 2026): a routine is bound to one computer and
can't be moved to another, and the jobs moved. This does the same job on the machine that runs build_glossary.py,
once a day:

  1. read ~/socialscope_data/glossary_pending.json (terms with no meaning yet; sample lines already have names
     replaced with [user] and links removed by build_glossary.py);
  2. ask Claude for one entry per term, from those lines only. Claude gets no tools: it can't read or write files,
     only answer in a fixed JSON shape;
  3. check every entry, then merge into ~/socialscope_data/glossary_definitions.json (kept entries unchanged,
     atomic write). The next hourly build_glossary.py run publishes them, sensitive ones held back.

Checks on each entry (an entry that fails is dropped and logged, the term stays pending for the next day):
- its key is one of the pending keys; kind is one of the allowed kinds;
- a definition is present unless the entry is marked sensitive (a sensitive one keeps no definition);
- the definition does not repeat any sample line (16+ characters copied from a sample);
- the definition has no @, link or [user] placeholder.

  python define_pending.py [--max 40] [--dry-run]
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

H = lambda p: os.path.expanduser(p)
KINDS = ["emote", "nickname", "meme", "phrase", "reference", "person", "event", "other"]
LABEL = "Claude scheduled task (from chat lines)"   # same label as the routine's entries, so the site reads alike

SYSTEM = """You write entries for a public glossary of destiny.gg (DGG) livestream chat, a community around the
political streamer Destiny. Entries are published automatically with no human review, labeled "Written by Claude
from chat lines only, unreviewed", so accuracy and caution matter more than coverage.

Source rule: each definition comes ONLY from the chat context given for that term: its sample lines, the words it
appears with, its counts and its archive note. Do not use the DGG wiki, web knowledge or what an emote or term means
elsewhere or where it comes from. If the lines don't make the meaning clear, describe what chat uses it for
("Posted when ... alongside ...").

For each term:
- definition: one or two plain sentences on what the term means in DGG chat and how chat is using it, judged from the
  lines alone. Say "appears to" when unsure. Make no claims of fact about real people beyond who or what the lines
  show the term refers to. Never copy a sample line or quote chat. Never include a username.
- kind: one of emote, nickname, meme, phrase, reference, person, event, other.
- sensitive: true if the term is a slur or slur substitute; a self-harm insult; harassment or a pile-on aimed at
  someone; sexual content; an allegation about a real person's private life, health or crimes; or the name or
  nickname of a private person caught up in a drama. When true, leave definition empty and give a short reason;
  the term is then held back and never published.
- reason: short reason when sensitive, else empty.
Return one entry per term, keyed by the term's "key"."""

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["entries"], "properties": {
    "entries": {"type": "array", "items": {"type": "object", "additionalProperties": False,
                "required": ["key", "definition", "kind", "sensitive", "reason"], "properties": {
                    "key": {"type": "string"}, "definition": {"type": "string"},
                    "kind": {"type": "string", "enum": KINDS}, "sensitive": {"type": "boolean"},
                    "reason": {"type": "string"}}}}}}


def ask(terms, model, effort, timeout):
    """One `claude -p` call on the subscription with no tools; returns the structured answer."""
    env = {k: v for k, v in os.environ.items()
           if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_BASE_URL", "CLAUDE_CODE_USE_BEDROCK",
                        "CLAUDE_CODE_USE_VERTEX", "ANTHROPIC_MODEL")}
    env["PATH"] = str(Path.home() / ".local" / "bin") + os.pathsep + env.get("PATH", "")
    fields = ("key", "term", "kind", "messages_24h", "chatters_24h", "lift", "archive_note", "co", "samples")
    text = ("Write one entry for each of these terms. The term data (JSON):\n"
            + json.dumps([{k: t.get(k) for k in fields} for t in terms], ensure_ascii=False, indent=1))
    args = ["claude", "-p", "--model", model, "--effort", effort, "--output-format", "json", "--no-session-persistence",
            "--strict-mcp-config", "--disable-slash-commands", "--setting-sources", "", "--tools", "",
            "--system-prompt", SYSTEM, "--json-schema", json.dumps(SCHEMA)]
    p = subprocess.run(args, input=text, capture_output=True, text=True, encoding="utf-8", env=env,
                       cwd=tempfile.gettempdir(), timeout=timeout)
    try:
        out = json.loads(p.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude exited {p.returncode}: {(p.stderr or p.stdout)[:300]}")
    if out.get("is_error") or not isinstance(out.get("structured_output"), dict):
        raise RuntimeError(f"claude returned no answer: {str(out.get('result'))[:300]}")
    return out["structured_output"]["entries"]


def problem(e, term):
    if e["kind"] not in KINDS:
        return "bad kind"
    d = e["definition"].strip()
    if e["sensitive"]:
        return None if e["reason"].strip() else "sensitive without a reason"
    if not d:
        return "empty definition"
    if re.search(r"@|https?://|www\.|\[user\]", d, re.I):
        return "has @, a link or [user]"
    # copying check: 24+ characters (3+ words) of a sample appearing in the definition. The term itself and the
    # words it appears with are taken out first, since a definition naming them is not a copy of a line.
    names = [w.lower() for w in [term.get("term", ""), *term.get("co", [])] if w]
    strip = lambda x: re.sub(r"\s+", " ", re.sub("|".join(map(re.escape, names)) or r"(?!)", " ", x.lower())).strip()
    low = strip(d)
    for s in term.get("samples", []):
        s = strip(s)
        for i in range(0, max(0, len(s) - 23)):
            chunk = s[i:i + 24]
            if len(chunk.split()) >= 3 and chunk in low:
                return "repeats a sample line"
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pending", default=H("~/socialscope_data/glossary_pending.json"))
    ap.add_argument("--definitions", default=H("~/socialscope_data/glossary_definitions.json"))
    ap.add_argument("--max", type=int, default=40)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--effort", default="medium")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--dry-run", action="store_true", help="ask Claude and check, but write nothing")
    a = ap.parse_args()

    pending = json.load(open(a.pending, encoding="utf-8")).get("terms", [])[:a.max]
    if not pending:
        print("define_pending: nothing pending")
        return 0
    by_key = {t["key"]: t for t in pending}
    try:
        defs = json.load(open(a.definitions, encoding="utf-8"))
    except FileNotFoundError:
        defs = {"terms": {}}
    entries = ask(pending, a.model, a.effort, a.timeout)
    try:
        today = dt.datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    except Exception:          # Windows Python has no tz database without the tzdata package; the PC runs on ET
        today = dt.date.today().isoformat()
    ok = held = 0
    for e in entries:
        t = by_key.get(e.get("key"))
        if t is None:
            print(f"  dropped: a key that was not pending")
            continue
        why = problem(e, t)
        if why:
            print(f"  dropped {e['key']!r}: {why}")
            continue
        defs["terms"][e["key"]] = {"definition": "" if e["sensitive"] else e["definition"].strip()[:400],
                                   "kind": e["kind"], "sensitive": bool(e["sensitive"]),
                                   "reason": e["reason"].strip()[:200], "date": today, "model": LABEL, "basis": "chat"}
        ok += 1
        held += bool(e["sensitive"])
        if a.dry_run:      # only Claude's wording is shown (it is what gets published), never sample lines
            print(f"  {e['key']} [{e['kind']}{', HELD: ' + e['reason'] if e['sensitive'] else ''}]: {e['definition']}")
    missing = len(by_key) - len({e.get("key") for e in entries} & set(by_key))
    print(f"define_pending: {len(pending)} pending, {ok} written ({held} held as sensitive), "
          f"{len(entries) - ok} dropped, {missing} not answered")
    if a.dry_run or not ok:
        return 0 if ok or a.dry_run else 1
    tmp = a.definitions + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        json.dump(defs, f, ensure_ascii=False, indent=1)
    os.replace(tmp, a.definitions)
    print(f"define_pending: {a.definitions} now has {len(defs['terms'])} entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
rate_limit_calendar.py — Claude Code Stop/StopFailure hook.

Detects the "You've hit your session limit · resets HH:MMam (Timezone)"
banner that Claude Code writes into the session transcript when the API
returns a 429 (rate_limit) response, and creates a Google Calendar event
at the reset time so the user knows when to resume (they reconnect via
RustDesk).

Why this exists / how it works:
- There is no documented "usage limit reached" hook event in Claude Code.
- The rate-limit banner IS persisted into the session's transcript JSONL
  as an assistant-role message with "error":"rate_limit",
  "isApiErrorMessage":true, and text like:
    "You've hit your session limit · resets 2:50am (America/Los_Angeles)"
  (confirmed by grepping real ~/.claude/projects/*/*.jsonl transcripts).
- The Stop/StopFailure hooks fire at the end of every turn and are given
  `transcript_path` in their stdin JSON (documented field). This script
  reads the tail of that file, looks for the rate-limit marker, and if
  found (and not already handled for this session+reset-time), creates
  a calendar event.

Calendar creation itself cannot be done from a plain shell/Python hook
(no Google API credentials/gcalcli are configured on this machine).
Instead this script shells out to a fresh, non-interactive `claude -p`
invocation that is explicitly allowed to use ONLY the
`mcp__claude_ai_Google_Calendar__create_event` tool (already connected to
this account via claude.ai — confirmed with `claude mcp list`).

NOTE: `--bare` mode was tried and rejected — it restricts auth to
ANTHROPIC_API_KEY/apiKeyHelper only ("OAuth and keychain are never read"),
so it cannot authenticate on a Max-plan OAuth login and always fails with
"Not logged in". Plain `claude -p` (no --bare) correctly reuses the
existing OAuth session. `--dangerously-skip-permissions` is required
since there is no human present to approve the tool call; the blast
radius is bounded by `--allowedTools` restricting the child to exactly
one MCP tool. Recursion is not a concern: the child's own transcript
will not contain a rate-limit banner (that would only happen if the
child call itself got rate-limited, which would legitimately warrant
its own calendar event, not an infinite loop).

As a robust fallback (in case the headless MCP call fails, is slow, or
the account connector is briefly down), an .ics file is always written
to ~/Downloads/ and the event details are always logged, and a desktop
notification is fired via notify-send.

De-duplication: keyed on (session_id, reset_at ISO string), stored in
SEEN_FILE, so repeated Stop events for the same rate-limit hit don't
create repeat calendar entries.

INSTALL: this file must be copied to ~/.claude/hooks/rate_limit_calendar.py
and wired into ~/.claude/settings.json under Stop / StopFailure hooks
(see docs in this repo / conversation for the settings.json snippet).
It is kept in this repo for version control since the harness would not
allow Write access directly into ~/.claude/hooks.
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HOOK_DIR = Path.home() / ".claude" / "hooks"
LOG_FILE = HOOK_DIR / "rate_limit_calendar.log"
SEEN_FILE = HOOK_DIR / ".rate_limit_calendar_seen.json"
ICS_DIR = Path.home() / "Downloads"

EVENT_TITLE = "Claude Max window reset"
EVENT_DURATION_MIN = 15

# Matches: "You've hit your session limit · resets 2:50am (America/Los_Angeles)"
# also tolerate "hit your ... limit" variants (weekly/opus/etc.) seen in the
# CLI source, and either "·" or "-" as separator, with/without a space before am/pm.
RATE_LIMIT_RE = re.compile(
    r"hit your .*?limit.*?resets\s+(\d{1,2}:\d{2}\s?[ap]m)\s*\(([^)]+)\)",
    re.IGNORECASE,
)


def log(msg: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write(f"{datetime.now().isoformat()} {msg}\n")


def load_seen() -> dict:
    if SEEN_FILE.exists():
        try:
            return json.loads(SEEN_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_seen(seen: dict) -> None:
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text(json.dumps(seen, indent=2))


def find_rate_limit_message(transcript_path: str, tail_lines: int = 20):
    """Return (time_str, tz_str, raw_text) from the last rate-limit banner
    found in the last `tail_lines` of the transcript, or None."""
    p = Path(transcript_path)
    if not p.exists():
        return None
    try:
        lines = p.read_text(errors="replace").splitlines()
    except Exception as e:
        log(f"ERROR reading transcript {transcript_path}: {e}")
        return None

    for line in reversed(lines[-tail_lines:]):
        if '"error":"rate_limit"' not in line and "rate_limit" not in line:
            continue
        m = RATE_LIMIT_RE.search(line)
        if m:
            return m.group(1), m.group(2), line
    return None


def parse_reset_datetime(time_str: str, tz_str: str) -> datetime:
    """Parse e.g. '2:50am' + 'America/Los_Angeles' into the next absolute
    occurrence of that wall-clock time in that timezone."""
    time_str = time_str.strip().lower().replace(" ", "")
    m = re.match(r"^(\d{1,2}):(\d{2})(am|pm)$", time_str)
    if not m:
        raise ValueError(f"Unrecognised time format: {time_str!r}")
    hour, minute, ampm = int(m.group(1)), int(m.group(2)), m.group(3)
    if ampm == "pm" and hour != 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0

    try:
        tz = ZoneInfo(tz_str)
    except Exception:
        # Fall back to UTC if the timezone name isn't recognised locally.
        log(f"WARNING unknown tz {tz_str!r}, falling back to UTC")
        tz = ZoneInfo("UTC")

    now = datetime.now(tz)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def already_handled(seen: dict, session_id: str, reset_iso: str) -> bool:
    return seen.get(session_id) == reset_iso


def write_ics(reset_dt: datetime) -> Path:
    ICS_DIR.mkdir(parents=True, exist_ok=True)
    dtstamp = datetime.now(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    dtstart = reset_dt.astimezone(ZoneInfo("UTC")).strftime("%Y%m%dT%H%M%SZ")
    dtend = (reset_dt + timedelta(minutes=EVENT_DURATION_MIN)).astimezone(
        ZoneInfo("UTC")
    ).strftime("%Y%m%dT%H%M%SZ")
    uid = f"claude-reset-{dtstart}@local"
    fname = ICS_DIR / f"claude_reset_{dtstart}.ics"
    ics = (
        "BEGIN:VCALENDAR\r\n"
        "VERSION:2.0\r\n"
        "PRODID:-//claude-code-hooks//rate_limit_calendar//EN\r\n"
        "BEGIN:VEVENT\r\n"
        f"UID:{uid}\r\n"
        f"DTSTAMP:{dtstamp}\r\n"
        f"DTSTART:{dtstart}\r\n"
        f"DTEND:{dtend}\r\n"
        f"SUMMARY:{EVENT_TITLE}\r\n"
        "DESCRIPTION:Auto-created after Claude Code hit its Max usage limit."
        " Resume the session via RustDesk.\r\n"
        "END:VEVENT\r\n"
        "END:VCALENDAR\r\n"
    )
    fname.write_text(ics)
    return fname


def create_via_headless_claude(reset_dt: datetime) -> bool:
    """Shell out to a narrowly-scoped, non-interactive claude -p invocation
    that is only allowed to call the Google Calendar MCP create_event tool.
    Returns True if the subprocess exits 0 (best-effort signal of success;
    the .ics/log fallback always runs regardless).

    The prompt is passed via stdin, not as a positional CLI argument:
    --allowedTools takes a variadic list, so a positional prompt string
    placed after it gets silently swallowed as an extra (bogus) tool name,
    leaving no prompt at all (observed empirically -- the CLI then errors
    with "Input must be provided either through stdin or as a prompt
    argument"). Piping via stdin sidesteps the ambiguity entirely.
    """
    start_iso = reset_dt.isoformat()
    end_iso = (reset_dt + timedelta(minutes=EVENT_DURATION_MIN)).isoformat()
    prompt = (
        "Use the mcp__claude_ai_Google_Calendar__create_event tool to create "
        f"exactly one calendar event titled \"{EVENT_TITLE}\" starting at "
        f"{start_iso} and ending at {end_iso} (these are already timezone-aware "
        "ISO 8601 timestamps, use them as given), with description "
        "\"Auto-created after Claude Code hit its Max usage limit. Resume the "
        "session via RustDesk.\" Call the tool once, then stop. Do not ask "
        "any questions and do not do anything else."
    )
    try:
        proc = subprocess.run(
            [
                "claude",
                "-p",
                "--allowedTools",
                "mcp__claude_ai_Google_Calendar__create_event",
                "--dangerously-skip-permissions",
            ],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=120,
        )
        log(f"headless claude exit={proc.returncode} stdout={proc.stdout[:500]!r} "
            f"stderr={proc.stderr[:500]!r}")
        return proc.returncode == 0
    except Exception as e:
        log(f"ERROR invoking headless claude: {e}")
        return False


def notify(reset_dt: datetime) -> None:
    msg = f"Resumes at {reset_dt.strftime('%H:%M %Z')} on {reset_dt.strftime('%Y-%m-%d')}"
    try:
        subprocess.run(
            ["notify-send", "Claude Max limit hit", msg],
            check=False,
            timeout=5,
        )
    except Exception as e:
        log(f"notify-send failed: {e}")


def main() -> int:
    try:
        hook_input = json.load(sys.stdin)
    except Exception as e:
        log(f"ERROR parsing hook stdin JSON: {e}")
        return 0  # never block the CLI

    transcript_path = hook_input.get("transcript_path")
    session_id = hook_input.get("session_id", "unknown")
    if not transcript_path:
        return 0

    found = find_rate_limit_message(transcript_path)
    if not found:
        return 0

    time_str, tz_str, raw_line = found
    try:
        reset_dt = parse_reset_datetime(time_str, tz_str)
    except Exception as e:
        log(f"ERROR parsing reset time {time_str!r}/{tz_str!r}: {e}")
        return 0

    reset_iso = reset_dt.isoformat()
    seen = load_seen()
    if already_handled(seen, session_id, reset_iso):
        return 0  # already created a calendar event for this exact hit

    log(f"DETECTED rate limit hit, session={session_id} reset={reset_iso} "
        f"raw={raw_line[:200]!r}")

    ics_path = write_ics(reset_dt)
    log(f"wrote ics: {ics_path}")

    ok = create_via_headless_claude(reset_dt)
    log(f"headless calendar creation {'succeeded' if ok else 'failed (ics fallback available)'}")

    notify(reset_dt)

    seen[session_id] = reset_iso
    save_seen(seen)
    return 0


if __name__ == "__main__":
    sys.exit(main())

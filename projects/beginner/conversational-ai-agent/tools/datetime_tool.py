"""DateTime tool — current date/time, timezone conversions, date arithmetic."""

from datetime import datetime, timedelta, timezone
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from langchain_core.tools import tool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_local_tz_now() -> tuple[datetime, str]:
    """Return (local_datetime, display_label) using the OS system clock.

    Uses datetime.now().astimezone() which reads the host OS timezone
    setting — no extra package required, works on Windows and Linux.
    """
    local = datetime.now().astimezone()
    offset = local.utcoffset()
    total_secs = int(offset.total_seconds()) if offset else 0
    sign = "+" if total_secs >= 0 else "-"
    h, m = divmod(abs(total_secs), 3600)
    m //= 60
    label = "UTC" if total_secs == 0 else f"UTC{sign}{h:02d}:{m:02d}"
    # Try to get a real IANA name from the tzinfo key (works when tzdata installed)
    tz_key = getattr(local.tzinfo, "key", None)
    if tz_key:
        label = f"{tz_key} ({label})"
    return local, label


def _get_tz(name: str) -> ZoneInfo | timezone:
    """Resolve an IANA name to a tzinfo. Raises ValueError with helpful message on failure."""
    if not name or name.upper() in ("UTC", "Z", "GMT"):
        return timezone.utc
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, KeyError):
        raise ValueError(
            f"Unknown timezone '{name}'. "
            "Use an IANA name like 'Asia/Karachi', 'America/New_York', 'Europe/London', "
            "or call action='list_timezones' to see all options."
        )


@tool
def datetime_tool(
    action: Annotated[
        str,
        "One of: 'now', 'convert', 'add', 'diff', 'list_timezones'. Default: 'now'.",
    ] = "now",
    timezone_name: Annotated[
        str,
        (
            "IANA timezone name, e.g. 'Asia/Karachi', 'America/New_York', 'Europe/London'. "
            "Leave EMPTY to auto-use the system's local timezone. "
            "Only set this when the user explicitly mentions a specific location/timezone "
            "different from where the server is running."
        ),
    ] = "",
    target_timezone: Annotated[
        str,
        "Target IANA timezone for 'convert' action, e.g. 'Asia/Tokyo'.",
    ] = "",
    date_string: Annotated[
        str,
        "ISO date/datetime string for 'convert', 'add', or 'diff'. E.g. '2026-05-20T14:30:00'.",
    ] = "",
    days: Annotated[int, "Days to add (negative = subtract) for 'add' action."] = 0,
    hours: Annotated[int, "Hours to add (negative = subtract) for 'add' action."] = 0,
    end_date: Annotated[str, "End date for 'diff' action (ISO format)."] = "",
) -> str:
    """Get the current date/time, convert timezones, or do date arithmetic.

    IMPORTANT — when the user asks "what time/date is it?" with NO location
    mentioned: call with action='now' and leave timezone_name empty.
    The tool will automatically use the server's system clock and timezone.
    Do NOT guess or default to UTC — leave it empty.

    Actions:
      now           — Current datetime (system timezone if timezone_name is empty).
      convert       — Convert a datetime string from one timezone to another.
      add           — Add/subtract days and/or hours from a datetime.
      diff          — Difference in days/hours between two dates.
      list_timezones— Print all available IANA timezone names.
    """
    try:
        # ── list_timezones ──────────────────────────────────────────────────
        if action == "list_timezones":
            common = sorted(
                tz
                for tz in available_timezones()
                if any(
                    tz.startswith(p)
                    for p in ("America/", "Europe/", "Asia/", "Africa/", "Australia/", "Pacific/")
                )
            )
            return "Available IANA timezones (common subset):\n" + "\n".join(
                f"  {tz}" for tz in common[:80]
            )

        # ── now ─────────────────────────────────────────────────────────────
        if action == "now":
            if not timezone_name:
                # Auto-detect: use OS system clock + timezone
                now, tz_label = _get_local_tz_now()
                source = "system clock"
            else:
                tz = _get_tz(timezone_name)
                now = datetime.now(tz)
                tz_label = timezone_name
                source = f"timezone '{timezone_name}'"
            return (
                f"Current date/time ({source}):\n"
                f"  Timezone : {tz_label}\n"
                f"  Date     : {now.strftime('%A, %B %d, %Y')}\n"
                f"  Time     : {now.strftime('%I:%M:%S %p')}\n"
                f"  ISO 8601 : {now.isoformat()}\n"
                f"  Day      : Day {now.timetuple().tm_yday} of {now.year}, "
                f"week {now.isocalendar().week}"
            )

        # ── convert ─────────────────────────────────────────────────────────
        if action == "convert":
            if not target_timezone:
                return (
                    "Error: 'convert' requires target_timezone. "
                    "E.g. target_timezone='America/New_York'. "
                    "Call list_timezones for options."
                )
            src_tz = _get_tz(timezone_name) if timezone_name else _get_local_tz_now()[0].tzinfo
            dt = (
                datetime.fromisoformat(date_string).replace(tzinfo=src_tz)
                if date_string
                else datetime.now(src_tz)
            )
            tgt_tz = _get_tz(target_timezone)
            converted = dt.astimezone(tgt_tz)
            src_label = timezone_name or "system"
            return (
                f"Conversion result:\n"
                f"  From : {dt.isoformat()} ({src_label})\n"
                f"  To   : {converted.isoformat()} ({target_timezone})\n"
                f"  Date : {converted.strftime('%A, %B %d, %Y')}\n"
                f"  Time : {converted.strftime('%I:%M:%S %p %Z')}"
            )

        # ── add ─────────────────────────────────────────────────────────────
        if action == "add":
            if timezone_name:
                tz = _get_tz(timezone_name)
                base = datetime.fromisoformat(date_string).replace(tzinfo=tz) if date_string else datetime.now(tz)
            else:
                base = datetime.fromisoformat(date_string) if date_string else _get_local_tz_now()[0]
            result = base + timedelta(days=days, hours=hours)
            parts = []
            if days:
                parts.append(f"{days:+d} day{'s' if abs(days) != 1 else ''}")
            if hours:
                parts.append(f"{hours:+d} hour{'s' if abs(hours) != 1 else ''}")
            delta_str = ", ".join(parts) or "0"
            return (
                f"Date arithmetic:\n"
                f"  Start  : {base.isoformat()}\n"
                f"  Delta  : {delta_str}\n"
                f"  Result : {result.isoformat()}\n"
                f"  Result : {result.strftime('%A, %B %d, %Y %I:%M %p')}"
            )

        # ── diff ────────────────────────────────────────────────────────────
        if action == "diff":
            if not date_string or not end_date:
                return "Error: 'diff' requires both date_string (start) and end_date (end)."
            d1 = datetime.fromisoformat(date_string)
            d2 = datetime.fromisoformat(end_date)
            delta = d2 - d1
            total_hours = int(delta.total_seconds() // 3600)
            total_minutes = int(delta.total_seconds() // 60)
            return (
                f"Date difference:\n"
                f"  From     : {date_string}\n"
                f"  To       : {end_date}\n"
                f"  Days     : {delta.days}\n"
                f"  Hours    : {total_hours}\n"
                f"  Minutes  : {total_minutes}"
            )

        return (
            f"Unknown action: '{action}'. "
            "Use 'now', 'convert', 'add', 'diff', or 'list_timezones'."
        )

    except Exception as e:
        return f"Error: {e}"

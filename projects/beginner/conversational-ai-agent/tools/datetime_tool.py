"""DateTime tool — current date/time, timezone conversions, date arithmetic."""

from datetime import datetime, timedelta, timezone
from typing import Annotated
from zoneinfo import ZoneInfo, available_timezones

from langchain_core.tools import tool


@tool
def datetime_tool(
    action: Annotated[
        str,
        "One of: 'now', 'convert', 'add', 'diff', 'list_timezones'",
    ] = "now",
    timezone_name: Annotated[
        str,
        "IANA timezone like 'America/New_York', 'Europe/London', 'Asia/Tokyo'. Default: UTC",
    ] = "UTC",
    target_timezone: Annotated[
        str,
        "Target timezone for 'convert' action.",
    ] = "",
    date_string: Annotated[
        str,
        "ISO date/datetime string, e.g. '2026-05-20' or '2026-05-20T14:30:00'",
    ] = "",
    days: Annotated[int, "Number of days to add (for 'add' action). Can be negative."] = 0,
    hours: Annotated[int, "Number of hours to add (for 'add' action). Can be negative."] = 0,
    end_date: Annotated[str, "End date for 'diff' action (ISO format)."] = "",
) -> str:
    """Get current date/time, convert between timezones, or do date arithmetic.

    Actions:
      - 'now': Current date and time in the given timezone.
      - 'convert': Convert a datetime from one timezone to another.
      - 'add': Add days/hours to a date.
      - 'diff': Calculate the difference between two dates.
      - 'list_timezones': List common timezones.
    """
    try:
        if action == "list_timezones":
            common = sorted(
                tz
                for tz in available_timezones()
                if any(
                    tz.startswith(p)
                    for p in ("America/", "Europe/", "Asia/", "Australia/", "Pacific/", "UTC")
                )
            )
            return "Common timezones:\n" + "\n".join(f"  - {tz}" for tz in common[:50])

        tz = ZoneInfo(timezone_name)

        if action == "now":
            now = datetime.now(tz)
            return (
                f"Current date/time in {timezone_name}:\n"
                f"  Date: {now.strftime('%A, %B %d, %Y')}\n"
                f"  Time: {now.strftime('%I:%M:%S %p')}\n"
                f"  ISO:  {now.isoformat()}"
            )

        if action == "convert":
            if not date_string:
                dt = datetime.now(tz)
            else:
                dt = datetime.fromisoformat(date_string).replace(tzinfo=tz)
            target_tz = ZoneInfo(target_timezone) if target_timezone else ZoneInfo("UTC")
            converted = dt.astimezone(target_tz)
            return (
                f"{dt.isoformat()} ({timezone_name})\n"
                f"  → {converted.isoformat()} ({target_timezone or 'UTC'})"
            )

        if action == "add":
            if date_string:
                dt = datetime.fromisoformat(date_string).replace(tzinfo=tz)
            else:
                dt = datetime.now(tz)
            result = dt + timedelta(days=days, hours=hours)
            return (
                f"Start:  {dt.isoformat()}\n"
                f"+ {days} days, {hours} hours\n"
                f"Result: {result.isoformat()}"
            )

        if action == "diff":
            if not date_string or not end_date:
                return "Error: 'diff' requires both date_string and end_date."
            d1 = datetime.fromisoformat(date_string)
            d2 = datetime.fromisoformat(end_date)
            delta = d2 - d1
            return (
                f"From: {date_string}\n"
                f"To:   {end_date}\n"
                f"Difference: {delta.days} days, {delta.seconds // 3600} hours"
            )

        return f"Unknown action: '{action}'. Use 'now', 'convert', 'add', 'diff', or 'list_timezones'."

    except Exception as e:
        return f"Error: {e}"

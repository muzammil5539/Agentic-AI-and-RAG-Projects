"""Code Interpreter tool — executes Python code in a sandboxed subprocess."""

import asyncio
import sys
import textwrap
from typing import Annotated

from langchain_core.tools import tool

# Hard limits to prevent runaway execution
_TIMEOUT_SECONDS = 30
_MAX_OUTPUT_CHARS = 8_000


@tool
async def code_interpreter(
    code: Annotated[str, "Valid Python code to execute. Always print() the result."],
    description: Annotated[str, "One-line description of what this code does."] = "",
) -> str:
    """Execute Python code in a sandboxed subprocess and return stdout + stderr.

    Use this for:
    - Arithmetic, statistics, and data processing too complex for the calculator
    - String manipulation, regex, parsing
    - Sorting, filtering, transforming lists/dicts
    - Date/time arithmetic beyond datetime_tool
    - Generating formatted tables or reports
    - Verifying algorithmic logic

    Rules:
    - Always include print() statements so results appear in the output.
    - Do NOT attempt file I/O, network requests, or subprocess calls inside the code.
    - Keep code self-contained (no imports that aren't in the standard library).
    - Execution is killed after 30 seconds.
    """
    # Dedent in case the model indents the whole block
    clean_code = textwrap.dedent(code).strip()

    header = f"# {description}\n" if description else ""
    full_code = header + clean_code

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            full_code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                proc.communicate(), timeout=_TIMEOUT_SECONDS
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return (
                f"❌ Execution timed out after {_TIMEOUT_SECONDS}s.\n"
                "Simplify the code or break it into smaller steps."
            )

        stdout = stdout_bytes.decode(errors="replace").strip()
        stderr = stderr_bytes.decode(errors="replace").strip()
        exit_code = proc.returncode

        parts: list[str] = [f"```python\n{clean_code}\n```\n"]

        if stdout:
            output = stdout[:_MAX_OUTPUT_CHARS]
            if len(stdout) > _MAX_OUTPUT_CHARS:
                output += f"\n… (truncated, {len(stdout)} chars total)"
            parts.append(f"**Output:**\n```\n{output}\n```")

        if stderr:
            err = stderr[:2_000]
            parts.append(f"**Stderr / Error:**\n```\n{err}\n```")

        if not stdout and not stderr:
            parts.append("*(no output — add print() statements to see results)*")

        status = "✅ Success" if exit_code == 0 else f"❌ Exit code {exit_code}"
        parts.insert(1, status)

        return "\n\n".join(parts)

    except Exception as exc:
        return f"❌ Failed to run code: {exc}"

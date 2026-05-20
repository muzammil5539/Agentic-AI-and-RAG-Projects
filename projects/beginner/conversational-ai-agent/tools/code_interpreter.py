"""Code Interpreter tool — executes Python code via OpenAI's code interpreter."""

from typing import Annotated

from langchain_core.tools import tool


@tool
async def code_interpreter(
    code: Annotated[str, "Python code to execute"],
    description: Annotated[str, "Brief description of what this code does"] = "",
) -> str:
    """Execute Python code using OpenAI's built-in code interpreter.

    Use this for:
    - Data analysis and calculations
    - String manipulation
    - Generating charts or visualizations
    - Processing structured data (CSV, JSON)
    - Running algorithms

    Note: This tool delegates to OpenAI's native code interpreter when available.
    """
    # This is a placeholder — actual code execution is handled by OpenAI's
    # code_interpreter tool binding on the ChatOpenAI model.
    # For safety, we don't execute arbitrary code on the server.
    return (
        f"Code interpreter request:\n"
        f"Description: {description}\n"
        f"Code:\n```python\n{code}\n```\n"
        "Note: Code execution is handled by OpenAI's code interpreter. "
        "If you're seeing this, the model's built-in code interpreter "
        "was not available for this request."
    )

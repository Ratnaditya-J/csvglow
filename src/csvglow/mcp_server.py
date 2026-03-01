"""MCP server for csvglow — exposes generate_dashboard as a tool."""

from __future__ import annotations

from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("csvglow")


@mcp.tool()
def generate_dashboard(
    file_path: str,
    output_path: Optional[str] = None,
    open_browser: bool = True,
) -> dict:
    """Generate a beautiful, interactive HTML dashboard from a CSV or Excel file.

    Analyzes the data and produces charts, statistics, correlations, insights,
    and a sortable data table — all in a single self-contained HTML file.

    Use this tool when the user wants to visualize, explore, analyze, or
    create a dashboard from a CSV, TSV, XLS, or XLSX file.

    Args:
        file_path: Absolute path to a CSV, TSV, XLS, or XLSX file.
        output_path: Where to save the HTML dashboard. Defaults to <input>.html.
        open_browser: Whether to auto-open the dashboard in the browser.
    """
    from csvglow.core import generate
    from csvglow.browser import open_in_browser

    html_path = generate(file_path=file_path, output_path=output_path)

    if open_browser:
        open_in_browser(html_path)

    return {
        "success": True,
        "message": f"Dashboard generated at {html_path}",
        "output_path": html_path,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")

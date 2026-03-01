"""CLI entry point for csvglow."""

from __future__ import annotations

import argparse
import sys

from csvglow import __version__


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="csvglow",
        description="Generate beautiful HTML dashboards from CSV/Excel files",
    )
    parser.add_argument("file", nargs="?", help="Path to CSV, XLS, or XLSX file")
    parser.add_argument(
        "-o", "--output",
        help="Output HTML file path (default: <input>.html)",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Don't auto-open the dashboard in the browser",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=50_000,
        help="Max rows for visualizations (default: 50000)",
    )
    parser.add_argument(
        "--mcp",
        action="store_true",
        help="Start as an MCP server (stdio transport) instead of generating a dashboard",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"csvglow {__version__}",
    )
    args = parser.parse_args()

    # MCP server mode
    if args.mcp:
        try:
            from csvglow.mcp_server import mcp
            mcp.run(transport="stdio")
        except ImportError:
            print(
                "Error: MCP dependencies not installed.\n"
                "Install with: pip install csvglow[mcp]",
                file=sys.stderr,
            )
            sys.exit(1)
        return

    # Normal dashboard mode — file is required
    if not args.file:
        parser.error("the following arguments are required: file\n"
                      "  Usage: csvglow data.csv\n"
                      "  Or:    csvglow --mcp  (start MCP server)")

    try:
        from csvglow.core import generate
        from csvglow.browser import open_in_browser

        print(f"Reading {args.file}...")
        output = generate(
            file_path=args.file,
            output_path=args.output,
            max_sample_rows=args.sample_size,
        )
        print(f"Dashboard saved to {output}")

        if not args.no_open:
            open_in_browser(output)

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

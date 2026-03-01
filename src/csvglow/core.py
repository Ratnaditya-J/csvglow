"""Core pipeline: file path → HTML dashboard.

Shared by CLI and MCP server.
"""

from __future__ import annotations

import pathlib

from csvglow.reader import read_file
from csvglow.sampler import smart_sample
from csvglow.analyzer import analyze
from csvglow.chart_config import build_all_charts
from csvglow.renderer import render_dashboard


def generate(
    file_path: str,
    output_path: str | None = None,
    max_sample_rows: int = 50_000,
) -> str:
    """Generate an HTML dashboard from a CSV/Excel file.

    Returns the path to the generated HTML file.
    """
    path = pathlib.Path(file_path).resolve()
    filename = path.stem

    # Read
    df = read_file(str(path))

    # Sample
    df_full, df_sampled = smart_sample(df, max_rows=max_sample_rows)

    # Analyze
    analysis = analyze(df_full, df_sampled)

    # Build charts
    charts = build_all_charts(analysis, df_sampled)

    # Render
    html = render_dashboard(analysis, charts, filename=filename)

    # Write
    if output_path is None:
        output_path = str(path.with_suffix(".html"))

    pathlib.Path(output_path).write_text(html, encoding="utf-8")
    return output_path

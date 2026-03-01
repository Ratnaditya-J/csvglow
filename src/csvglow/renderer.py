"""Render analysis results into a self-contained HTML dashboard."""

from __future__ import annotations

import importlib.resources
import json

import jinja2

from csvglow.analyzer import AnalysisResult


def load_echarts_js() -> str:
    """Load the bundled echarts.min.js content."""
    assets = importlib.resources.files("csvglow") / "assets" / "echarts.min.js"
    return assets.read_text(encoding="utf-8")


def render_dashboard(
    analysis: AnalysisResult,
    charts: list[dict],
    filename: str = "data",
) -> str:
    """Render the complete HTML dashboard as a string."""
    echarts_js = load_echarts_js()

    env = jinja2.Environment(
        loader=jinja2.PackageLoader("csvglow", "templates"),
        autoescape=False,  # HTML template, we control the data
    )
    template = env.get_template("dashboard.html.j2")

    # Prepare chart JSON (options only, for JS initialization)
    charts_for_js = [
        {"chart_id": c["chart_id"], "option": c["option"]}
        for c in charts
    ]

    # Column type counts
    type_counts = {}
    total_missing = 0
    total_cells = 0
    for col in analysis.columns:
        type_counts[col.dtype] = type_counts.get(col.dtype, 0) + 1
        total_missing += col.missing_count
        total_cells += analysis.row_count

    missing_pct = (total_missing / total_cells * 100) if total_cells > 0 else 0

    table_columns = [col.name for col in analysis.columns]
    table_row_count = len(analysis.data_sample) if analysis.data_sample else 0

    return template.render(
        filename=filename,
        analysis=analysis,
        charts=charts,
        charts_json=json.dumps(charts_for_js, ensure_ascii=False),
        echarts_js=echarts_js,
        numeric_count=type_counts.get("numeric", 0),
        categorical_count=type_counts.get("categorical", 0),
        datetime_count=type_counts.get("datetime", 0),
        missing_pct=missing_pct,
        data_table_json=json.dumps(analysis.data_sample or [], ensure_ascii=False),
        table_columns=table_columns,
        table_columns_json=json.dumps(table_columns),
        table_row_count=table_row_count,
    )

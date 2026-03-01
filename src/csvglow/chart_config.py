"""Build ECharts option dictionaries for each chart type."""

from __future__ import annotations

from csvglow.analyzer import AnalysisResult, ColumnProfile, CrossAnalysis


# -- Theme constants -----------------------------------------------------------

COLORS = [
    "#667eea", "#764ba2", "#f093fb", "#f5576c", "#4facfe",
    "#00f2fe", "#43e97b", "#fa709a", "#fee140", "#a18cd1",
]

GRADIENT_BAR = {
    "type": "linear",
    "x": 0, "y": 0, "x2": 0, "y2": 1,
    "colorStops": [
        {"offset": 0, "color": "#667eea"},
        {"offset": 0.5, "color": "#764ba2"},
        {"offset": 1, "color": "#f093fb"},
    ],
}

DARK = {
    "bg": "#0f0f1a",
    "cardBg": "rgba(255,255,255,0.04)",
    "text": "#e0e0e0",
    "textSub": "#888",
    "axis": "#333",
    "split": "#222",
}


# -- Shared helpers ------------------------------------------------------------

def _base_option(title: str) -> dict:
    """Common option fields for all charts."""
    return {
        "backgroundColor": "transparent",
        "title": {
            "text": title,
            "left": "center",
            "textStyle": {"color": DARK["text"], "fontSize": 14, "fontWeight": 500},
        },
        "tooltip": {"trigger": "axis", "backgroundColor": "#1a1a2e", "borderColor": "#333"},
        "grid": {"left": 60, "right": 30, "top": 50, "bottom": 40, "containLabel": True},
    }


def _axis_style() -> dict:
    return {
        "axisLine": {"lineStyle": {"color": DARK["axis"]}},
        "axisLabel": {"color": DARK["textSub"], "fontSize": 11},
        "splitLine": {"lineStyle": {"color": DARK["split"], "type": "dashed"}},
    }


# -- Chart builders ------------------------------------------------------------

def build_histogram(col: ColumnProfile) -> dict | None:
    """Histogram for a numeric column."""
    if not col.histogram_bins or not col.histogram_counts:
        return None

    bins = col.histogram_bins
    counts = col.histogram_counts
    labels = [f"{bins[i]:.1f}" for i in range(len(counts))]

    option = _base_option(f"Distribution of {col.name}")
    option["xAxis"] = {
        "type": "category",
        "data": labels,
        **_axis_style(),
    }
    option["yAxis"] = {"type": "value", **_axis_style()}
    option["series"] = [{
        "type": "bar",
        "data": counts,
        "itemStyle": {
            "borderRadius": [4, 4, 0, 0],
            "color": GRADIENT_BAR,
        },
        "emphasis": {
            "itemStyle": {
                "color": {
                    "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "#8b9cf7"},
                        {"offset": 0.5, "color": "#9a6bc4"},
                        {"offset": 1, "color": "#f5b3fc"},
                    ],
                }
            }
        },
    }]
    option["tooltip"]["trigger"] = "item"

    return {
        "chart_id": f"hist_{_safe_id(col.name)}",
        "chart_type": "histogram",
        "title": f"Distribution of {col.name}",
        "column": col.name,
        "option": option,
        "stats": col.stats,
        "outlier_count": col.outlier_count,
    }


def build_bar_chart(col: ColumnProfile) -> dict | None:
    """Bar chart for a categorical column's value counts."""
    if not col.value_counts:
        return None

    categories = list(col.value_counts.keys())
    values = list(col.value_counts.values())

    # Assign gradient colors per bar
    color_stops = []
    for i, _ in enumerate(categories):
        c = COLORS[i % len(COLORS)]
        color_stops.append(c)

    option = _base_option(f"Top values: {col.name}")
    option["xAxis"] = {
        "type": "category",
        "data": categories,
        "axisLabel": {
            "color": DARK["textSub"],
            "fontSize": 11,
            "rotate": 30 if len(categories) > 8 else 0,
            "interval": 0,
        },
        "axisLine": {"lineStyle": {"color": DARK["axis"]}},
    }
    option["yAxis"] = {"type": "value", **_axis_style()}
    option["series"] = [{
        "type": "bar",
        "data": [
            {"value": v, "itemStyle": {"color": color_stops[i], "borderRadius": [4, 4, 0, 0]}}
            for i, v in enumerate(values)
        ],
    }]
    option["tooltip"]["trigger"] = "item"

    return {
        "chart_id": f"bar_{_safe_id(col.name)}",
        "chart_type": "bar",
        "title": f"Top values: {col.name}",
        "column": col.name,
        "option": option,
    }


def build_line_chart(col: ColumnProfile, df, date_col: str, value_col: str) -> dict | None:
    """Time series line chart for a date column paired with a numeric column."""
    import pandas as pd

    dates = pd.to_datetime(df[date_col], errors="coerce")
    values = pd.to_numeric(df[value_col], errors="coerce")
    mask = dates.notna() & values.notna()
    dates = dates[mask]
    values = values[mask]

    if len(dates) == 0:
        return None

    # Sort by date
    sort_idx = dates.argsort()
    date_labels = [str(d.date()) for d in dates.iloc[sort_idx]]
    value_data = [round(float(v), 2) for v in values.iloc[sort_idx]]

    option = _base_option(f"{value_col} over {date_col}")
    option["xAxis"] = {
        "type": "category",
        "data": date_labels,
        "axisLabel": {"color": DARK["textSub"], "fontSize": 11, "rotate": 30},
        "axisLine": {"lineStyle": {"color": DARK["axis"]}},
    }
    option["yAxis"] = {"type": "value", **_axis_style()}
    option["series"] = [{
        "type": "line",
        "data": value_data,
        "smooth": True,
        "symbol": "none",
        "lineStyle": {"width": 2, "color": "#667eea"},
        "areaStyle": {
            "color": {
                "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                "colorStops": [
                    {"offset": 0, "color": "rgba(102,126,234,0.4)"},
                    {"offset": 1, "color": "rgba(102,126,234,0.02)"},
                ],
            }
        },
    }]
    option["dataZoom"] = [{"type": "inside"}, {"type": "slider", "height": 20, "bottom": 5}]

    return {
        "chart_id": f"line_{_safe_id(date_col)}_{_safe_id(value_col)}",
        "chart_type": "line",
        "title": f"{value_col} over {date_col}",
        "column": date_col,
        "option": option,
    }


def build_scatter(col_x: str, col_y: str, x_data: list, y_data: list, r: float) -> dict | None:
    """Scatter plot for two correlated numeric columns."""
    if not x_data or not y_data:
        return None

    data = [[round(float(x), 2), round(float(y), 2)] for x, y in zip(x_data, y_data)]

    option = _base_option(f"{col_x} vs {col_y} (r={r:.2f})")
    option["xAxis"] = {"type": "value", "name": col_x, **_axis_style()}
    option["yAxis"] = {"type": "value", "name": col_y, **_axis_style()}
    option["series"] = [{
        "type": "scatter",
        "data": data,
        "symbolSize": 5,
        "itemStyle": {"color": "#667eea", "opacity": 0.6},
    }]
    option["tooltip"] = {
        "trigger": "item",
        "backgroundColor": "#1a1a2e",
        "borderColor": "#333",
        "formatter": f"{{c}}",
    }

    return {
        "chart_id": f"scatter_{_safe_id(col_x)}_{_safe_id(col_y)}",
        "chart_type": "scatter",
        "title": f"{col_x} vs {col_y} (r={r:.2f})",
        "option": option,
    }


def build_heatmap(labels: list[str], matrix: list[list[float]]) -> dict | None:
    """Correlation heatmap for numeric columns."""
    if not labels or not matrix:
        return None

    # ECharts heatmap data: [x_index, y_index, value]
    data = []
    for i in range(len(labels)):
        for j in range(len(labels)):
            val = matrix[i][j]
            if val != val:  # NaN check
                val = 0
            data.append([j, i, round(val, 2)])

    option = _base_option("Correlation Matrix")
    option["grid"] = {"left": 120, "right": 60, "top": 50, "bottom": 100}
    option["xAxis"] = {
        "type": "category",
        "data": labels,
        "axisLabel": {"color": DARK["textSub"], "fontSize": 10, "rotate": 45, "interval": 0},
        "axisLine": {"lineStyle": {"color": DARK["axis"]}},
        "splitArea": {"show": False},
    }
    option["yAxis"] = {
        "type": "category",
        "data": labels,
        "axisLabel": {"color": DARK["textSub"], "fontSize": 10, "interval": 0},
        "axisLine": {"lineStyle": {"color": DARK["axis"]}},
        "splitArea": {"show": False},
    }
    option["visualMap"] = {
        "min": -1,
        "max": 1,
        "calculable": True,
        "orient": "horizontal",
        "left": "center",
        "bottom": 5,
        "inRange": {
            "color": ["#f093fb", "#1a1a2e", "#667eea"],
        },
        "textStyle": {"color": DARK["textSub"]},
    }
    option["series"] = [{
        "type": "heatmap",
        "data": data,
        "label": {
            "show": len(labels) <= 10,
            "color": DARK["text"],
            "fontSize": 10,
        },
        "emphasis": {"itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.5)"}},
    }]
    option["tooltip"] = {
        "trigger": "item",
        "backgroundColor": "#1a1a2e",
        "borderColor": "#333",
    }

    return {
        "chart_id": "heatmap_correlation",
        "chart_type": "heatmap",
        "title": "Correlation Matrix",
        "option": option,
    }


def build_date_counts_chart(col: ColumnProfile) -> dict | None:
    """Bar/line chart showing record counts per time period."""
    if not col.date_counts_by_period:
        return None

    periods = list(col.date_counts_by_period.keys())
    counts = list(col.date_counts_by_period.values())

    option = _base_option(f"Records over time ({col.name})")
    option["xAxis"] = {
        "type": "category",
        "data": periods,
        "axisLabel": {"color": DARK["textSub"], "fontSize": 11, "rotate": 30},
        "axisLine": {"lineStyle": {"color": DARK["axis"]}},
    }
    option["yAxis"] = {"type": "value", **_axis_style()}
    option["series"] = [{
        "type": "bar",
        "data": counts,
        "itemStyle": {
            "borderRadius": [4, 4, 0, 0],
            "color": GRADIENT_BAR,
        },
    }]
    option["tooltip"]["trigger"] = "item"

    return {
        "chart_id": f"datecounts_{_safe_id(col.name)}",
        "chart_type": "line",  # grouped with time series section
        "title": f"Records over time ({col.name})",
        "column": col.name,
        "option": option,
    }


def build_crosstab_chart(cross: CrossAnalysis) -> dict | None:
    """Grouped bar chart: average numeric by categorical, with overall mean line."""
    data = cross.chart_data
    if not data or not data.get("categories"):
        return None

    categories = data["categories"]
    values = data["values"]
    overall_mean = data["overall_mean"]

    option = _base_option(cross.title)
    option["xAxis"] = {
        "type": "category",
        "data": categories,
        "axisLabel": {
            "color": DARK["textSub"],
            "fontSize": 11,
            "rotate": 30 if len(categories) > 6 else 0,
            "interval": 0,
        },
        "axisLine": {"lineStyle": {"color": DARK["axis"]}},
    }
    option["yAxis"] = {"type": "value", **_axis_style()}
    option["series"] = [
        {
            "type": "bar",
            "data": [
                {
                    "value": v,
                    "itemStyle": {
                        "color": COLORS[i % len(COLORS)],
                        "borderRadius": [4, 4, 0, 0],
                    },
                }
                for i, v in enumerate(values)
            ],
            "name": f"Avg {data['num_col']}",
        },
        {
            "type": "line",
            "markLine": {
                "silent": True,
                "symbol": "none",
                "lineStyle": {"color": "#f5576c", "type": "dashed", "width": 1.5},
                "label": {
                    "formatter": f"Overall avg: {overall_mean:,.0f}",
                    "color": "#f5576c",
                    "fontSize": 11,
                },
                "data": [{"yAxis": overall_mean}],
            },
            "data": [],
        },
    ]
    option["tooltip"]["trigger"] = "item"

    return {
        "chart_id": f"crosstab_{_safe_id(data['cat_col'])}_{_safe_id(data['num_col'])}",
        "chart_type": "crosstab",
        "title": cross.title,
        "description": cross.description,
        "option": option,
    }


def build_all_charts(analysis: AnalysisResult, df_sampled) -> list[dict]:
    """Build all chart configs from analysis results."""
    import pandas as pd

    charts = []

    # Only chart columns that are worth charting
    chartworthy = [c for c in analysis.columns if c.is_chartworthy]

    date_cols = [c for c in chartworthy if c.dtype == "datetime"]
    numeric_cols = [c for c in chartworthy if c.dtype == "numeric"]

    for col in chartworthy:
        if col.dtype == "numeric":
            chart = build_histogram(col)
            if chart:
                charts.append(chart)
        elif col.dtype == "categorical":
            # Skip categoricals where every value is unique (not interesting)
            if col.unique_count > 0 and col.value_counts:
                max_count = max(col.value_counts.values())
                if max_count > 1 or len(col.value_counts) <= 20:
                    chart = build_bar_chart(col)
                    if chart:
                        charts.append(chart)

    # Date columns: show aggregated counts (e.g. "signups per month")
    for dcol in date_cols:
        chart = build_date_counts_chart(dcol)
        if chart:
            charts.append(chart)

    # Time series: pair date columns with chartworthy numeric columns only
    for dcol in date_cols:
        for ncol in numeric_cols[:3]:
            chart = build_line_chart(dcol, df_sampled, dcol.name, ncol.name)
            if chart:
                charts.append(chart)

    # Correlation heatmap
    if analysis.correlation_matrix:
        chart = build_heatmap(analysis.correlation_labels, analysis.correlation_matrix)
        if chart:
            charts.append(chart)

    # Cross-analyses: crosstab charts
    for cross in analysis.cross_analyses:
        if cross.analysis_type == "crosstab" and cross.chart_data:
            chart = build_crosstab_chart(cross)
            if chart:
                charts.append(chart)

    # Scatter plots for high correlations
    for col_x, col_y, r in analysis.high_correlations:
        x_data = pd.to_numeric(df_sampled[col_x], errors="coerce").dropna()
        y_data = pd.to_numeric(df_sampled[col_y], errors="coerce").dropna()
        common = x_data.index.intersection(y_data.index)
        if len(common) > 2000:
            common = common[:2000]
        chart = build_scatter(col_x, col_y, x_data[common].tolist(), y_data[common].tolist(), r)
        if chart:
            charts.append(chart)

    return charts


def _safe_id(name: str) -> str:
    """Convert column name to a safe HTML id."""
    return "".join(c if c.isalnum() else "_" for c in name).strip("_")[:40]

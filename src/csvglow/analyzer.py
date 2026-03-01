"""Analyze DataFrame columns: types, stats, correlations, outliers."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class ColumnProfile:
    name: str
    dtype: str  # "numeric", "categorical", "datetime", "text", "identifier"
    missing_count: int = 0
    missing_pct: float = 0.0
    unique_count: int = 0
    is_chartworthy: bool = True  # False for identifiers, low-info columns
    # Numeric
    stats: dict | None = None
    histogram_bins: list[float] | None = None
    histogram_counts: list[int] | None = None
    outlier_count: int = 0
    # Categorical
    value_counts: dict[str, int] | None = None
    # Datetime
    date_range: tuple | None = None
    date_counts_by_period: dict[str, int] | None = None  # e.g. {"2021-01": 5, "2021-02": 8}


@dataclass
class CrossAnalysis:
    """A relationship found between two columns."""
    analysis_type: str  # "crosstab", "trend", "concentration"
    title: str
    description: str  # human-readable insight
    chart_data: dict | None = None  # data for chart rendering


@dataclass
class Insight:
    """A single auto-generated text finding."""
    icon: str  # emoji
    text: str
    severity: str = "info"  # "info", "warning", "highlight"


@dataclass
class AnalysisResult:
    row_count: int
    column_count: int
    columns: list[ColumnProfile] = field(default_factory=list)
    correlation_matrix: list[list[float]] | None = None
    correlation_labels: list[str] | None = None
    high_correlations: list[tuple[str, str, float]] = field(default_factory=list)
    cross_analyses: list[CrossAnalysis] = field(default_factory=list)
    insights: list[Insight] = field(default_factory=list)
    data_sample: list[dict] | None = None


def analyze(df_full: pd.DataFrame, df_sampled: pd.DataFrame) -> AnalysisResult:
    """Run full analysis on the DataFrame.

    df_full is used for stats (computed on all data).
    df_sampled is used for histogram bins / chart data.
    """
    result = AnalysisResult(
        row_count=len(df_full),
        column_count=len(df_full.columns),
    )

    for col_name in df_full.columns:
        series_full = df_full[col_name]
        series_sampled = df_sampled[col_name]

        # Check if this is an identifier column first
        is_id = _is_identifier_column(col_name, series_full)
        dtype = _detect_type(series_full)

        profile = _profile_column(col_name, dtype, series_full, series_sampled)
        profile.is_chartworthy = not is_id

        # For identifier columns, override dtype so they don't get charted
        if is_id:
            profile.dtype = "identifier"

        result.columns.append(profile)

    # Correlation matrix for chartworthy numeric columns only
    numeric_cols = [c for c in result.columns if c.dtype == "numeric" and c.is_chartworthy]
    if len(numeric_cols) >= 2:
        numeric_names = [c.name for c in numeric_cols]
        # Cap at 20 columns for readability
        if len(numeric_names) > 20:
            numeric_names = numeric_names[:20]

        corr_df = df_full[numeric_names].corr()
        result.correlation_labels = numeric_names
        result.correlation_matrix = corr_df.values.tolist()

        # Find high correlations (|r| > 0.7, excluding self-correlation)
        for i in range(len(numeric_names)):
            for j in range(i + 1, len(numeric_names)):
                r = corr_df.iloc[i, j]
                if abs(r) > 0.7 and not np.isnan(r):
                    result.high_correlations.append(
                        (numeric_names[i], numeric_names[j], round(r, 3))
                    )

        # Sort by absolute correlation, keep top 10
        result.high_correlations.sort(key=lambda x: abs(x[2]), reverse=True)
        result.high_correlations = result.high_correlations[:10]

    # ── Cross-column analysis ──────────────────────────────────────
    _discover_cross_analyses(result, df_full)
    _generate_insights(result, df_full)

    # Data sample for table (first 1000 rows)
    table_df = df_full.head(1000).copy()
    # Convert datetime columns to strings for JSON serialization
    for col in table_df.columns:
        if pd.api.types.is_datetime64_any_dtype(table_df[col]):
            table_df[col] = table_df[col].astype(str)
    result.data_sample = table_df.fillna("").to_dict(orient="records")

    return result


import re
import warnings

# Patterns that indicate a column is an identifier, not analytical data
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_URL_RE = re.compile(r"^https?://")
_UUID_RE = re.compile(r"^[0-9a-fA-F]{8,}[-]?[0-9a-fA-F]{4,}")
_PHONE_RE = re.compile(r"^[\d\s\-\+\(\)\.x]{7,}$")

_ID_NAME_HINTS = {"id", "uuid", "guid", "key", "token", "hash", "code"}
_SKIP_NAME_HINTS = {"email", "url", "website", "link", "href", "phone", "fax", "mobile", "cell"}


def _is_identifier_column(name: str, series: pd.Series) -> bool:
    """Detect if a column is an identifier (not worth charting)."""
    name_lower = name.lower().replace("_", " ").replace("-", " ")
    n = len(series)
    non_null = series.dropna()
    if len(non_null) == 0:
        return True

    # Check column name hints
    name_parts = set(name_lower.split())
    if name_parts & _ID_NAME_HINTS:
        return True
    if name_parts & _SKIP_NAME_HINTS:
        return True

    # Numeric column that's sequential (row counter / index)
    if pd.api.types.is_numeric_dtype(series):
        numeric = pd.to_numeric(series, errors="coerce").dropna()
        if len(numeric) > 1:
            diffs = numeric.diff().dropna()
            if (diffs == 1).mean() > 0.9:  # 90%+ sequential increments
                return True

    # String columns: sample and check patterns
    sample = non_null.head(20).astype(str)
    if len(sample) > 0:
        email_rate = sample.apply(lambda x: bool(_EMAIL_RE.match(x))).mean()
        if email_rate > 0.8:
            return True

        url_rate = sample.apply(lambda x: bool(_URL_RE.match(x))).mean()
        if url_rate > 0.8:
            return True

        phone_rate = sample.apply(lambda x: bool(_PHONE_RE.match(x))).mean()
        if phone_rate > 0.8:
            return True

        uuid_rate = sample.apply(lambda x: bool(_UUID_RE.match(x))).mean()
        if uuid_rate > 0.8:
            return True

    # Nearly all unique string values = likely identifier
    if not pd.api.types.is_numeric_dtype(series):
        if n > 0 and series.nunique() / n > 0.9:
            # High cardinality string — likely names, IDs, etc.
            avg_len = non_null.astype(str).str.len().mean()
            if avg_len > 5:  # Short codes might be categorical
                return True

    return False


def _detect_type(series: pd.Series) -> str:
    """Detect the semantic type of a column."""
    if pd.api.types.is_datetime64_any_dtype(series):
        return "datetime"

    if pd.api.types.is_numeric_dtype(series):
        return "numeric"

    # Try parsing as datetime
    non_null = series.dropna()
    if len(non_null) > 0:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                parsed = pd.to_datetime(non_null, errors="coerce")
            success_rate = parsed.notna().sum() / len(non_null)
            if success_rate > 0.8:
                return "datetime"
        except Exception:
            pass

    # Try parsing as numeric
    if len(non_null) > 0:
        try:
            parsed = pd.to_numeric(non_null, errors="coerce")
            success_rate = parsed.notna().sum() / len(non_null)
            if success_rate > 0.9:
                return "numeric"
        except Exception:
            pass

    # Categorical: reasonable cardinality for charting
    nunique = series.nunique()
    n = len(series)
    if n > 0:
        ratio = nunique / n
        if nunique <= 200 or ratio < 0.5:
            return "categorical"

    return "text"


def _profile_column(
    name: str,
    dtype: str,
    series_full: pd.Series,
    series_sampled: pd.Series,
) -> ColumnProfile:
    """Build a ColumnProfile for one column."""
    profile = ColumnProfile(
        name=name,
        dtype=dtype,
        missing_count=int(series_full.isna().sum()),
        missing_pct=round(series_full.isna().mean() * 100, 1),
        unique_count=int(series_full.nunique()),
    )

    if dtype == "numeric":
        _profile_numeric(profile, series_full, series_sampled)
    elif dtype == "categorical":
        _profile_categorical(profile, series_full)
    elif dtype == "datetime":
        _profile_datetime(profile, series_full)

    return profile


def _profile_numeric(
    profile: ColumnProfile,
    series_full: pd.Series,
    series_sampled: pd.Series,
) -> None:
    """Add numeric stats, histogram, outlier count."""
    # Coerce to numeric if stored as strings
    numeric_full = pd.to_numeric(series_full, errors="coerce").dropna()
    numeric_sampled = pd.to_numeric(series_sampled, errors="coerce").dropna()

    if len(numeric_full) == 0:
        return

    profile.stats = {
        "mean": round(float(numeric_full.mean()), 2),
        "median": round(float(numeric_full.median()), 2),
        "std": round(float(numeric_full.std()), 2),
        "min": round(float(numeric_full.min()), 2),
        "max": round(float(numeric_full.max()), 2),
        "q25": round(float(numeric_full.quantile(0.25)), 2),
        "q75": round(float(numeric_full.quantile(0.75)), 2),
    }

    # Histogram from sampled data
    n_bins = min(50, max(10, int(np.sqrt(len(numeric_sampled)))))
    counts, bin_edges = np.histogram(numeric_sampled, bins=n_bins)
    profile.histogram_bins = [round(float(b), 4) for b in bin_edges]
    profile.histogram_counts = [int(c) for c in counts]

    # Outlier count (IQR method on full data)
    q1, q3 = numeric_full.quantile(0.25), numeric_full.quantile(0.75)
    iqr = q3 - q1
    if iqr > 0:
        outliers = ((numeric_full < q1 - 1.5 * iqr) | (numeric_full > q3 + 1.5 * iqr)).sum()
        profile.outlier_count = int(outliers)


def _profile_categorical(profile: ColumnProfile, series_full: pd.Series) -> None:
    """Add value counts (top 20)."""
    vc = series_full.value_counts().head(20)
    profile.value_counts = {str(k): int(v) for k, v in vc.items()}


def _profile_datetime(profile: ColumnProfile, series_full: pd.Series) -> None:
    """Add date range and auto-aggregated counts by period."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        parsed = pd.to_datetime(series_full, errors="coerce").dropna()
    if len(parsed) == 0:
        return

    profile.date_range = (str(parsed.min()), str(parsed.max()))

    # Auto-detect best aggregation period
    span_days = (parsed.max() - parsed.min()).days
    if span_days <= 60:
        # Under 2 months: group by day
        periods = parsed.dt.strftime("%Y-%m-%d")
    elif span_days <= 730:
        # Under 2 years: group by month
        periods = parsed.dt.to_period("M").astype(str)
    else:
        # Longer: group by quarter
        periods = parsed.dt.to_period("Q").astype(str)

    counts = periods.value_counts().sort_index()
    profile.date_counts_by_period = {str(k): int(v) for k, v in counts.items()}


# ── Cross-column analysis ───────────────────────────────────────────────────

def _discover_cross_analyses(result: AnalysisResult, df: pd.DataFrame) -> None:
    """Find relationships between columns and generate cross-analyses."""
    cat_cols = [c for c in result.columns if c.dtype == "categorical" and c.is_chartworthy]
    num_cols = [c for c in result.columns if c.dtype == "numeric" and c.is_chartworthy]
    date_cols = [c for c in result.columns if c.dtype == "datetime" and c.is_chartworthy]

    # 1. Categorical × Numeric crosstabs: "Average Salary by Department"
    for cat in cat_cols:
        # Only use categoricals with 2-20 groups (too few = trivial, too many = unreadable)
        if cat.unique_count < 2 or cat.unique_count > 20:
            continue
        for num in num_cols:
            _add_crosstab(result, df, cat.name, num.name)
            if len(result.cross_analyses) >= 12:  # cap total cross-analyses
                return

    # 2. Date trend detection: is a numeric value trending over time?
    for dcol in date_cols:
        for ncol in num_cols[:3]:
            _add_trend_analysis(result, df, dcol.name, ncol.name)
            if len(result.cross_analyses) >= 12:
                return


def _add_crosstab(result: AnalysisResult, df: pd.DataFrame, cat_col: str, num_col: str) -> None:
    """Compute average of num_col grouped by cat_col. Add if interesting."""
    grouped = df.groupby(cat_col)[num_col].agg(["mean", "count"]).dropna()
    grouped = grouped[grouped["count"] >= 2]  # need at least 2 per group
    if len(grouped) < 2:
        return

    grouped = grouped.sort_values("mean", ascending=False).head(15)
    overall_mean = df[num_col].mean()

    # Is this interesting? Check if the spread between groups is significant
    if len(grouped) >= 2:
        ratio = grouped["mean"].max() / max(grouped["mean"].min(), 0.001)
        if ratio < 1.3:  # less than 30% difference = not interesting
            return

    categories = [str(k) for k in grouped.index]
    means = [round(float(v), 2) for v in grouped["mean"]]
    counts = [int(v) for v in grouped["count"]]

    # Find the top and bottom groups
    top_group = categories[0]
    top_val = means[0]
    bottom_group = categories[-1]
    bottom_val = means[-1]

    description = (
        f"{top_group} has the highest avg {num_col} ({top_val:,.0f}), "
        f"{bottom_group} has the lowest ({bottom_val:,.0f}). "
        f"Overall average: {overall_mean:,.0f}."
    )

    result.cross_analyses.append(CrossAnalysis(
        analysis_type="crosstab",
        title=f"Average {num_col} by {cat_col}",
        description=description,
        chart_data={
            "categories": categories,
            "values": means,
            "counts": counts,
            "overall_mean": round(float(overall_mean), 2),
            "cat_col": cat_col,
            "num_col": num_col,
        },
    ))


def _add_trend_analysis(
    result: AnalysisResult, df: pd.DataFrame, date_col: str, num_col: str
) -> None:
    """Detect if num_col is trending over date_col. Add insight if significant."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        dates = pd.to_datetime(df[date_col], errors="coerce")
    values = pd.to_numeric(df[num_col], errors="coerce")
    mask = dates.notna() & values.notna()

    if mask.sum() < 5:
        return

    # Group by period and compute mean
    combined = pd.DataFrame({"date": dates[mask], "value": values[mask]})
    combined = combined.sort_values("date")

    span_days = (combined["date"].max() - combined["date"].min()).days
    if span_days < 7:
        return

    if span_days <= 730:
        combined["period"] = combined["date"].dt.to_period("M").astype(str)
    else:
        combined["period"] = combined["date"].dt.to_period("Q").astype(str)

    period_means = combined.groupby("period")["value"].mean()
    if len(period_means) < 3:
        return

    # Simple trend: compare first third vs last third
    n = len(period_means)
    first_third = period_means.iloc[: n // 3].mean()
    last_third = period_means.iloc[-(n // 3):].mean()

    if first_third == 0:
        return

    pct_change = (last_third - first_third) / abs(first_third) * 100

    if abs(pct_change) < 10:  # less than 10% change = not a meaningful trend
        return

    direction = "up" if pct_change > 0 else "down"
    description = (
        f"{num_col} is trending {direction} by {abs(pct_change):.0f}% over the time range. "
        f"Early average: {first_third:,.0f}, recent average: {last_third:,.0f}."
    )

    result.cross_analyses.append(CrossAnalysis(
        analysis_type="trend",
        title=f"{num_col} trend over {date_col}",
        description=description,
        chart_data=None,  # uses existing time series chart
    ))


# ── Auto-generated insights ─────────────────────────────────────────────────

def _generate_insights(result: AnalysisResult, df: pd.DataFrame) -> None:
    """Generate top-level text insights about the dataset."""

    # 1. Missing data warning
    total_cells = result.row_count * result.column_count
    total_missing = sum(c.missing_count for c in result.columns)
    if total_cells > 0 and total_missing > 0:
        pct = total_missing / total_cells * 100
        worst_col = max(result.columns, key=lambda c: c.missing_pct)
        if pct > 1:
            result.insights.append(Insight(
                icon="⚠️",
                text=f"{pct:.1f}% of all values are missing. Worst: {worst_col.name} ({worst_col.missing_pct}% missing).",
                severity="warning",
            ))

    # 2. Concentration: does a small group dominate?
    for col in result.columns:
        if col.dtype == "categorical" and col.value_counts and col.is_chartworthy:
            total = sum(col.value_counts.values())
            if total == 0:
                continue
            top_val = list(col.value_counts.keys())[0]
            top_count = list(col.value_counts.values())[0]
            top_pct = top_count / result.row_count * 100
            if top_pct > 30:
                result.insights.append(Insight(
                    icon="📊",
                    text=f'"{top_val}" dominates {col.name} — {top_pct:.0f}% of all rows.',
                    severity="highlight",
                ))

            # Top 3 concentration
            top3_count = sum(list(col.value_counts.values())[:3])
            top3_pct = top3_count / result.row_count * 100
            if top3_pct > 60 and len(col.value_counts) > 5:
                top3_names = ", ".join(list(col.value_counts.keys())[:3])
                result.insights.append(Insight(
                    icon="🎯",
                    text=f"Top 3 {col.name} values ({top3_names}) account for {top3_pct:.0f}% of data.",
                    severity="info",
                ))

    # 3. Outlier summary
    outlier_cols = [(c.name, c.outlier_count) for c in result.columns
                    if c.dtype == "numeric" and c.outlier_count > 0 and c.is_chartworthy]
    if outlier_cols:
        total_outliers = sum(count for _, count in outlier_cols)
        worst = max(outlier_cols, key=lambda x: x[1])
        result.insights.append(Insight(
            icon="🔍",
            text=f"{total_outliers} outlier values detected across {len(outlier_cols)} columns. Most in {worst[0]} ({worst[1]} outliers).",
            severity="info",
        ))

    # 4. High correlation alert
    if result.high_correlations:
        top = result.high_correlations[0]
        direction = "positively" if top[2] > 0 else "negatively"
        result.insights.append(Insight(
            icon="🔗",
            text=f"{top[0]} and {top[1]} are strongly {direction} correlated (r={top[2]:.2f}).",
            severity="highlight",
        ))

    # 5. Date range insight
    for col in result.columns:
        if col.dtype == "datetime" and col.date_range and col.is_chartworthy:
            result.insights.append(Insight(
                icon="📅",
                text=f"{col.name} spans from {col.date_range[0][:10]} to {col.date_range[1][:10]}.",
                severity="info",
            ))

    # 6. Trend insights (from cross_analyses)
    for ca in result.cross_analyses:
        if ca.analysis_type == "trend":
            icon = "📈" if "up" in ca.description else "📉"
            result.insights.append(Insight(
                icon=icon,
                text=ca.description,
                severity="highlight",
            ))

    # 7. Multi-column narrative insights (the "smart" layer)
    _generate_multi_column_insights(result, df)

    # Cap at 15 insights (increased to allow narrative ones)
    result.insights = result.insights[:15]


def _generate_multi_column_insights(result: AnalysisResult, df: pd.DataFrame) -> None:
    """Generate nuanced insights that combine facts across multiple columns.

    For each categorical column with few groups, compute all numeric columns'
    averages per group. Cross-reference to find contradictions, anomalies,
    and actionable narratives like:
      "Gadget Y has the highest discount (15%) yet lowest revenue despite
       lowest cost — consider discontinuing."
    """
    cat_cols = [c for c in result.columns if c.dtype == "categorical" and c.is_chartworthy
                and 2 <= c.unique_count <= 15]
    num_cols = [c for c in result.columns if c.dtype == "numeric" and c.is_chartworthy]

    if not cat_cols or len(num_cols) < 2:
        return

    # Score each categorical by how much variance it creates across numeric cols.
    # Categoricals where groups look nearly identical (like Region in the sales data)
    # should be deprioritized vs ones with meaningful differences (like Product).
    cat_scores: list[tuple[float, ColumnProfile]] = []
    for cat in cat_cols:
        grouped = df.groupby(cat.name)
        group_counts = grouped.size()
        valid_groups = group_counts[group_counts >= 2].index.tolist()
        if len(valid_groups) < 3:
            cat_scores.append((0, cat))
            continue

        # Coefficient of variation of group means across numeric cols
        cv_sum = 0.0
        cv_count = 0
        for ncol in num_cols:
            means = grouped[ncol.name].mean().dropna()
            if len(means) >= 2 and means.mean() != 0:
                cv = float(means.std() / abs(means.mean()))
                cv_sum += cv
                cv_count += 1
        avg_cv = cv_sum / max(cv_count, 1)
        cat_scores.append((avg_cv, cat))

    # Sort by descending variance — most interesting categoricals first
    cat_scores.sort(key=lambda x: x[0], reverse=True)
    narrative_count = 0

    for _, cat in cat_scores:
        # Build a profile table: for each category value, compute avg of every numeric col
        groups = df.groupby(cat.name)
        group_counts = groups.size()
        valid_groups = group_counts[group_counts >= 2].index.tolist()
        if len(valid_groups) < 2:
            continue

        # Build metrics matrix: {group_name: {num_col: avg_value}}
        metrics: dict[str, dict[str, float]] = {}
        for g in valid_groups:
            metrics[str(g)] = {}
            for ncol in num_cols:
                vals = pd.to_numeric(groups.get_group(g)[ncol.name], errors="coerce").dropna()
                if len(vals) > 0:
                    metrics[str(g)][ncol.name] = float(vals.mean())

        if not metrics:
            continue

        num_col_names = [n.name for n in num_cols if all(n.name in m for m in metrics.values())]
        if len(num_col_names) < 2:
            continue

        # Build rankings: {num_col: [(group, value), ...] sorted desc}
        rankings: dict[str, list[tuple[str, float]]] = {}
        for ncol in num_col_names:
            ranked = sorted(
                [(g, metrics[g][ncol]) for g in metrics],
                key=lambda x: x[1], reverse=True,
            )
            rankings[ncol] = ranked

        before = len(result.insights)
        mentioned: set[str] = set()  # track groups already mentioned to avoid redundancy

        # --- Strategy 1: Find contradictions (high cost/discount but low revenue) ---
        _find_contradictions(result, rankings, metrics, num_col_names, cat.name, mentioned)

        # --- Strategy 2: Efficiency analysis (best/worst output per input) ---
        _find_efficiency_insights(result, rankings, metrics, num_col_names, cat.name)

        # --- Strategy 3: Find "worst performer" across multiple metrics ---
        _find_underperformers(result, rankings, metrics, num_col_names, cat.name, mentioned)

        # --- Strategy 4: Find "best performer" (top across multiple metrics) ---
        _find_top_performers(result, rankings, metrics, num_col_names, cat.name, mentioned)

        narrative_count += len(result.insights) - before
        if narrative_count >= 5:
            break


def _find_underperformers(
    result: AnalysisResult,
    rankings: dict[str, list[tuple[str, float]]],
    metrics: dict[str, dict[str, float]],
    num_cols: list[str],
    cat_col: str,
    mentioned: set[str] | None = None,
) -> None:
    """Find groups that underperform on key output metrics despite favorable inputs.

    E.g., "Gadget Y has the lowest revenue and lowest units despite having the
    lowest cost — consider discontinuing."
    """
    n_groups = len(next(iter(rankings.values())))
    if n_groups < 3:
        return

    # Classify columns by semantic role
    _output_hints = {"revenue", "sales", "income", "profit", "total", "amount", "price"}
    _input_hints = {"cost", "discount", "expense", "spend", "units", "quantity"}

    output_cols = [c for c in num_cols if any(h in c.lower() for h in _output_hints)]
    input_cols = [c for c in num_cols if any(h in c.lower() for h in _input_hints)]

    # If we can't classify, fall back to generic worst-in-multiple-metrics
    target_cols = output_cols if output_cols else num_cols

    # For each group, count how many output metrics it ranks last in
    bottom_counts: dict[str, list[str]] = {g: [] for g in metrics}
    for ncol in target_cols:
        ranked = rankings[ncol]
        last_group = ranked[-1][0]
        bottom_counts[last_group].append(ncol)

    for group, bottom_in in bottom_counts.items():
        if len(bottom_in) < 1:
            continue

        # Check if this group also has a favorable input position (low cost = advantage)
        # or unfavorable one (high cost/discount = should have better output)
        favorable_inputs = []  # "lowest cost" = advantage, makes underperformance worse
        unfavorable_inputs = []  # "highest discount" = investment, makes underperformance worse
        for ncol in input_cols:
            ranked = rankings[ncol]
            if ranked[-1][0] == group:  # lowest in this input
                favorable_inputs.append((ncol, metrics[group][ncol]))
            if ranked[0][0] == group:  # highest in this input
                unfavorable_inputs.append((ncol, metrics[group][ncol]))

        # Need at least: bad output + some input context
        if not favorable_inputs and not unfavorable_inputs and len(bottom_in) < 2:
            continue

        parts = []
        # What it's worst at (outputs)
        worst_details = []
        for col in bottom_in[:2]:
            val = metrics[group][col]
            worst_details.append(f"lowest {col} ({_fmt_num(val)})")
        parts.append(" and ".join(worst_details))

        # Despite favorable inputs (low cost = should be easy to profit)
        if favorable_inputs:
            fav_details = [f"lowest {c} ({_fmt_num(v)})" for c, v in favorable_inputs[:2]]
            parts.append("despite having " + " and ".join(fav_details))

        # Or despite high investment (high discount = should drive more sales)
        if unfavorable_inputs:
            unfav_details = [f"highest {c} ({_fmt_num(v)})" for c, v in unfavorable_inputs[:2]]
            if favorable_inputs:
                parts.append("and " + " and ".join(unfav_details))
            else:
                parts.append("despite having " + " and ".join(unfav_details))

        # Skip if this group was already mentioned in another insight
        if mentioned and group in mentioned:
            continue

        text = f"{group} has the {parts[0]}"
        for p in parts[1:]:
            text += f", {p}"
        text += ". May warrant review."

        result.insights.append(Insight(
            icon="🚩",
            text=text,
            severity="warning",
        ))
        if mentioned is not None:
            mentioned.add(group)
        return  # One underperformer insight is enough


def _find_top_performers(
    result: AnalysisResult,
    rankings: dict[str, list[tuple[str, float]]],
    metrics: dict[str, dict[str, float]],
    num_cols: list[str],
    cat_col: str,
    mentioned: set[str] | None = None,
) -> None:
    """Find groups that consistently rank first across metrics."""
    top_counts: dict[str, list[str]] = {g: [] for g in metrics}
    for ncol, ranked in rankings.items():
        top_group = ranked[0][0]
        top_counts[top_group].append(ncol)

    for group, top_in in top_counts.items():
        if len(top_in) >= 2 and (not mentioned or group not in mentioned):
            details = []
            for col in top_in[:3]:
                val = metrics[group][col]
                details.append(f"{col} ({_fmt_num(val)})")

            text = f"{group} leads in {', '.join(details)}."

            # Check if it also has a weakness
            for ncol, ranked in rankings.items():
                if ranked[-1][0] == group and ncol not in top_in:
                    weak_val = metrics[group][ncol]
                    text += f" However, it has the lowest {ncol} ({_fmt_num(weak_val)})."
                    break

            result.insights.append(Insight(
                icon="⭐",
                text=text,
                severity="highlight",
            ))
            if mentioned is not None:
                mentioned.add(group)
            return  # One top performer insight is enough


def _find_contradictions(
    result: AnalysisResult,
    rankings: dict[str, list[tuple[str, float]]],
    metrics: dict[str, dict[str, float]],
    num_cols: list[str],
    cat_col: str,
    mentioned: set[str] | None = None,
) -> None:
    """Find groups that are high in one metric but low in a related metric.

    Looks for patterns like "highest cost but lowest revenue" which suggest
    inefficiency or anomalies.
    """
    n_groups = len(next(iter(rankings.values())))
    if n_groups < 3:
        return

    # Revenue/sales-like columns (positive outcomes)
    _positive_hints = {"revenue", "sales", "income", "profit", "total", "amount", "price"}
    # Cost/effort-like columns (inputs)
    _negative_hints = {"cost", "discount", "expense", "spend", "loss", "debt", "churn"}

    positive_cols = [c for c in num_cols if any(h in c.lower() for h in _positive_hints)]
    negative_cols = [c for c in num_cols if any(h in c.lower() for h in _negative_hints)]

    if not positive_cols or not negative_cols:
        return

    # Find group that's high in a negative metric but low in a positive one
    for neg_col in negative_cols:
        neg_ranked = rankings[neg_col]
        high_neg_group = neg_ranked[0][0]
        high_neg_val = neg_ranked[0][1]

        for pos_col in positive_cols:
            pos_ranked = rankings[pos_col]
            # Where does this group rank in the positive metric?
            pos_rank = next(
                (i for i, (g, _) in enumerate(pos_ranked) if g == high_neg_group),
                None,
            )
            if pos_rank is not None and pos_rank >= len(pos_ranked) - 2:
                # Skip if already mentioned
                if mentioned and high_neg_group in mentioned:
                    continue
                # High in negative, low in positive — that's a contradiction
                pos_val = metrics[high_neg_group][pos_col]
                text = (
                    f"{high_neg_group} has the highest {neg_col} ({_fmt_num(high_neg_val)}) "
                    f"yet ranks near the bottom in {pos_col} ({_fmt_num(pos_val)}). "
                    f"This suggests poor ROI on {neg_col}."
                )
                result.insights.append(Insight(
                    icon="⚡",
                    text=text,
                    severity="warning",
                ))
                if mentioned is not None:
                    mentioned.add(high_neg_group)
                return  # One contradiction is enough


def _find_efficiency_insights(
    result: AnalysisResult,
    rankings: dict[str, list[tuple[str, float]]],
    metrics: dict[str, dict[str, float]],
    num_cols: list[str],
    cat_col: str,
) -> None:
    """Find groups with best/worst ratio between output and input metrics.

    E.g., highest (Revenue - Cost) / Cost, or lowest Revenue per Unit.
    """
    # Look for revenue/sales and cost/units pairs
    _output_hints = {"revenue", "sales", "income", "profit", "total", "amount"}
    _input_hints = {"cost", "units", "quantity", "count", "spend", "hours"}

    output_cols = [c for c in num_cols if any(h in c.lower() for h in _output_hints)]
    input_cols = [c for c in num_cols if any(h in c.lower() for h in _input_hints)]

    if not output_cols or not input_cols:
        return

    out_col = output_cols[0]
    in_col = input_cols[0]

    # Compute ratio for each group
    ratios = {}
    for g in metrics:
        if in_col in metrics[g] and out_col in metrics[g] and metrics[g][in_col] > 0:
            ratios[g] = metrics[g][out_col] / metrics[g][in_col]

    if len(ratios) < 3:
        return

    sorted_ratios = sorted(ratios.items(), key=lambda x: x[1], reverse=True)
    best_group, best_ratio = sorted_ratios[0]
    worst_group, worst_ratio = sorted_ratios[-1]

    # Only report if the spread is meaningful (2x+ difference)
    if best_ratio < worst_ratio * 1.5:
        return

    text = (
        f"{best_group} is the most efficient: {_fmt_num(best_ratio)} {out_col} per {in_col}. "
        f"{worst_group} is the least efficient at {_fmt_num(worst_ratio)}."
    )
    result.insights.append(Insight(
        icon="💡",
        text=text,
        severity="highlight",
    ))


def _fmt_num(val: float) -> str:
    """Format a number for insight text: use commas for large, decimals for small."""
    if abs(val) >= 1000:
        return f"{val:,.0f}"
    elif abs(val) >= 1:
        return f"{val:.1f}"
    elif val == 0:
        return "0"
    else:
        return f"{val:.2f}"

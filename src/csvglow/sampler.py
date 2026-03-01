"""Smart sampling for large DataFrames."""

from __future__ import annotations

import numpy as np
import pandas as pd


def smart_sample(
    df: pd.DataFrame, max_rows: int = 50_000
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (full_df, sampled_df).

    Stats should be computed on full_df.
    Visualizations should use sampled_df.

    If df fits within max_rows, both are the same object.
    Outlier rows are force-included in the sample.
    """
    if len(df) <= max_rows:
        return df, df

    # Identify outlier rows (any numeric column beyond 3*IQR)
    outlier_mask = pd.Series(False, index=df.index)
    numeric_cols = df.select_dtypes(include="number").columns

    for col in numeric_cols:
        q1 = df[col].quantile(0.25)
        q3 = df[col].quantile(0.75)
        iqr = q3 - q1
        if iqr > 0:
            lower = q1 - 3 * iqr
            upper = q3 + 3 * iqr
            outlier_mask |= (df[col] < lower) | (df[col] > upper)

    outlier_rows = df[outlier_mask]
    non_outlier_rows = df[~outlier_mask]

    # Budget for random sample
    budget = max(0, max_rows - len(outlier_rows))

    if budget > 0 and len(non_outlier_rows) > budget:
        sampled_non_outliers = non_outlier_rows.sample(n=budget, random_state=42)
    else:
        sampled_non_outliers = non_outlier_rows

    sampled = pd.concat([outlier_rows, sampled_non_outliers]).sort_index()
    return df, sampled

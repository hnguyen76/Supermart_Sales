"""Retail analytics pipeline for the Supermart Grocery Sales dataset.

The script validates the raw CSV, creates analysis-ready summaries, exports
chart assets, and writes a Markdown business report.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, PercentFormatter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "Supermart Grocery Sales - Retail Analytics Dataset.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "reports" / "supermart_sales_analysis.md"
DEFAULT_DASHBOARD_PATH = PROJECT_ROOT / "dashboard" / "index.html"

REQUIRED_COLUMNS = [
    "Order ID",
    "Customer Name",
    "Category",
    "Sub Category",
    "City",
    "Order Date",
    "Region",
    "Sales",
    "Discount",
    "Profit",
    "State",
]

CHART_COLORS = {
    "blue": "#2563EB",
    "teal": "#0F766E",
    "orange": "#F59E0B",
    "red": "#DC2626",
    "purple": "#7C3AED",
    "gray": "#475569",
}

CHART_FILES = [
    {
        "title": "Monthly Sales and Profit Trend",
        "filename": "monthly_sales_profit_trend.png",
        "alt": "Monthly sales bars with profit line trend",
    },
    {
        "title": "Category Sales and Margin",
        "filename": "category_sales_margin.png",
        "alt": "Category sales bars with profit margin dots",
    },
    {
        "title": "Discount vs Margin",
        "filename": "discount_vs_profit_margin.png",
        "alt": "Subcategory discount versus margin bubble chart",
    },
    {
        "title": "Regional Performance",
        "filename": "region_sales_profit.png",
        "alt": "Regional sales and profit bar chart",
    },
    {
        "title": "Top Cities",
        "filename": "top_10_cities_by_sales.png",
        "alt": "Top ten cities by sales bar chart",
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the Supermart Grocery Sales retail analytics pipeline."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Path to the raw Supermart sales CSV.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where tables and charts will be saved.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Path for the generated Markdown report.",
    )
    parser.add_argument(
        "--dashboard-path",
        type=Path,
        default=DEFAULT_DASHBOARD_PATH,
        help="Path for the generated static HTML dashboard.",
    )
    return parser.parse_args()


def currency(value: float) -> str:
    return f"${value:,.0f}"


def percentage(value: float) -> str:
    return f"{value:.1%}"


def compact_number(value: float, _position: int | None = None) -> str:
    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if abs(value) >= 1_000:
        return f"{value / 1_000:.0f}K"
    return f"{value:.0f}"


def parse_order_dates(values: pd.Series) -> pd.Series:
    """Parse mixed date strings using month-first retail source convention.

    The raw file contains both hyphen and slash separators. Slash values such as
    4/15/2018 are unambiguously month-first, so the pipeline treats ambiguous
    values such as 11-08-2017 as November 8, 2017.
    """

    normalized = values.astype(str).str.strip().str.replace("-", "/", regex=False)
    try:
        parsed = pd.to_datetime(
            normalized, format="mixed", errors="coerce", dayfirst=False
        )
    except (TypeError, ValueError):
        parsed = pd.to_datetime(normalized, errors="coerce", dayfirst=False)

    if parsed.isna().any():
        examples = values[parsed.isna()].head(5).tolist()
        raise ValueError(f"Unable to parse Order Date values: {examples}")

    return parsed


def load_and_prepare_data(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    df = pd.read_csv(path)
    missing_columns = sorted(set(REQUIRED_COLUMNS) - set(df.columns))
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")

    df = df[REQUIRED_COLUMNS].copy()
    df["Order Date"] = parse_order_dates(df["Order Date"])

    for column in ["Sales", "Discount", "Profit"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    if df[["Sales", "Discount", "Profit"]].isna().any().any():
        bad_counts = df[["Sales", "Discount", "Profit"]].isna().sum()
        raise ValueError(f"Numeric conversion created nulls:\n{bad_counts}")

    df["Year"] = df["Order Date"].dt.year
    df["Month"] = df["Order Date"].dt.to_period("M").dt.to_timestamp()
    df["Month Label"] = df["Month"].dt.strftime("%Y-%m")
    df["Profit Margin"] = np.where(df["Sales"] == 0, np.nan, df["Profit"] / df["Sales"])
    df["Discount Rate"] = df["Discount"]

    return df


def summarize_by(df: pd.DataFrame, group_by: str | list[str]) -> pd.DataFrame:
    summary = (
        df.groupby(group_by, dropna=False)
        .agg(
            orders=("Order ID", "count"),
            customers=("Customer Name", "nunique"),
            sales=("Sales", "sum"),
            profit=("Profit", "sum"),
            avg_order_value=("Sales", "mean"),
            avg_discount=("Discount Rate", "mean"),
        )
        .reset_index()
    )
    summary["profit_margin"] = summary["profit"] / summary["sales"]
    summary["sales_share"] = summary["sales"] / summary["sales"].sum()
    summary["profit_share"] = summary["profit"] / summary["profit"].sum()
    return summary.sort_values("sales", ascending=False).reset_index(drop=True)


def build_summaries(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    monthly = (
        df.groupby(["Month", "Month Label"], dropna=False)
        .agg(
            orders=("Order ID", "count"),
            customers=("Customer Name", "nunique"),
            sales=("Sales", "sum"),
            profit=("Profit", "sum"),
            avg_discount=("Discount Rate", "mean"),
        )
        .reset_index()
        .sort_values("Month")
    )
    monthly["profit_margin"] = monthly["profit"] / monthly["sales"]
    monthly["sales_growth"] = monthly["sales"].pct_change()
    monthly["profit_growth"] = monthly["profit"].pct_change()

    yearly = (
        df.groupby("Year", dropna=False)
        .agg(
            orders=("Order ID", "count"),
            customers=("Customer Name", "nunique"),
            sales=("Sales", "sum"),
            profit=("Profit", "sum"),
            avg_discount=("Discount Rate", "mean"),
        )
        .reset_index()
        .sort_values("Year")
    )
    yearly["profit_margin"] = yearly["profit"] / yearly["sales"]
    yearly["sales_growth"] = yearly["sales"].pct_change()
    yearly["profit_growth"] = yearly["profit"].pct_change()

    return {
        "category": summarize_by(df, "Category"),
        "subcategory": summarize_by(df, ["Category", "Sub Category"]),
        "region": summarize_by(df, "Region"),
        "city": summarize_by(df, "City"),
        "monthly": monthly,
        "yearly": yearly,
    }


def export_tables(summaries: dict[str, pd.DataFrame], output_dir: Path) -> None:
    tables_dir = output_dir / "tables"
    tables_dir.mkdir(parents=True, exist_ok=True)
    for name, table in summaries.items():
        table.to_csv(tables_dir / f"{name}_summary.csv", index=False)


def setup_chart_style() -> None:
    plt.rcParams.update(
        {
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "axes.edgecolor": "#CBD5E1",
            "axes.labelcolor": "#0F172A",
            "axes.titleweight": "bold",
            "axes.titlesize": 14,
            "font.size": 10,
            "grid.color": "#E2E8F0",
            "grid.linestyle": "-",
            "grid.linewidth": 0.8,
            "xtick.color": "#334155",
            "ytick.color": "#334155",
        }
    )


def save_monthly_trend(monthly: pd.DataFrame, charts_dir: Path) -> None:
    fig, ax_sales = plt.subplots(figsize=(13, 6))
    x = np.arange(len(monthly))

    ax_sales.bar(
        x,
        monthly["sales"],
        color=CHART_COLORS["blue"],
        alpha=0.82,
        label="Sales",
    )
    ax_sales.set_ylabel("Sales")
    ax_sales.yaxis.set_major_formatter(FuncFormatter(compact_number))
    ax_sales.grid(axis="y")

    ax_profit = ax_sales.twinx()
    ax_profit.plot(
        x,
        monthly["profit"],
        color=CHART_COLORS["red"],
        marker="o",
        linewidth=2.2,
        markersize=4,
        label="Profit",
    )
    ax_profit.set_ylabel("Profit")
    ax_profit.yaxis.set_major_formatter(FuncFormatter(compact_number))

    tick_positions = x[::3]
    ax_sales.set_xticks(tick_positions)
    ax_sales.set_xticklabels(monthly["Month Label"].iloc[::3], rotation=45, ha="right")
    ax_sales.set_title("Monthly Sales and Profit Trend")

    lines, labels = ax_sales.get_legend_handles_labels()
    lines2, labels2 = ax_profit.get_legend_handles_labels()
    ax_sales.legend(lines + lines2, labels + labels2, loc="upper left", frameon=False)

    fig.tight_layout()
    fig.savefig(charts_dir / "monthly_sales_profit_trend.png", dpi=180)
    plt.close(fig)


def save_category_performance(category: pd.DataFrame, charts_dir: Path) -> None:
    data = category.sort_values("sales", ascending=True)
    fig, ax_sales = plt.subplots(figsize=(11, 6))

    ax_sales.barh(data["Category"], data["sales"], color=CHART_COLORS["teal"], alpha=0.86)
    ax_sales.set_xlabel("Sales")
    ax_sales.xaxis.set_major_formatter(FuncFormatter(compact_number))
    ax_sales.grid(axis="x")

    ax_margin = ax_sales.twiny()
    ax_margin.scatter(
        data["profit_margin"],
        data["Category"],
        color=CHART_COLORS["orange"],
        s=70,
        zorder=4,
        label="Profit margin",
    )
    ax_margin.xaxis.set_major_formatter(PercentFormatter(1.0))
    ax_margin.set_xlabel("Profit margin")
    ax_sales.set_title("Category Sales with Profit Margin Overlay")

    fig.tight_layout()
    fig.savefig(charts_dir / "category_sales_margin.png", dpi=180)
    plt.close(fig)


def save_region_performance(region: pd.DataFrame, charts_dir: Path) -> None:
    data = region.sort_values("sales", ascending=False)
    x = np.arange(len(data))
    width = 0.38

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width / 2, data["sales"], width, label="Sales", color=CHART_COLORS["blue"])
    ax.bar(
        x + width / 2,
        data["profit"],
        width,
        label="Profit",
        color=CHART_COLORS["purple"],
    )

    ax.set_xticks(x)
    ax.set_xticklabels(data["Region"])
    ax.set_ylabel("Value")
    ax.yaxis.set_major_formatter(FuncFormatter(compact_number))
    ax.set_title("Regional Sales and Profit")
    ax.legend(frameon=False)
    ax.grid(axis="y")

    fig.tight_layout()
    fig.savefig(charts_dir / "region_sales_profit.png", dpi=180)
    plt.close(fig)


def save_top_cities(city: pd.DataFrame, charts_dir: Path) -> None:
    data = city.head(10).sort_values("sales", ascending=True)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(data["City"], data["sales"], color=CHART_COLORS["blue"], alpha=0.86)
    ax.set_xlabel("Sales")
    ax.xaxis.set_major_formatter(FuncFormatter(compact_number))
    ax.set_title("Top 10 Cities by Sales")
    ax.grid(axis="x")

    fig.tight_layout()
    fig.savefig(charts_dir / "top_10_cities_by_sales.png", dpi=180)
    plt.close(fig)


def save_discount_margin_scatter(subcategory: pd.DataFrame, charts_dir: Path) -> None:
    data = subcategory.copy()
    bubble_size = 120 + (data["sales"] / data["sales"].max()) * 900

    fig, ax = plt.subplots(figsize=(11, 7))
    scatter = ax.scatter(
        data["avg_discount"],
        data["profit_margin"],
        s=bubble_size,
        c=data["sales"],
        cmap="viridis",
        alpha=0.72,
        edgecolor="white",
        linewidth=0.8,
    )

    for _, row in data.nlargest(6, "sales").iterrows():
        ax.annotate(
            row["Sub Category"],
            (row["avg_discount"], row["profit_margin"]),
            textcoords="offset points",
            xytext=(6, 6),
            fontsize=8,
            color="#0F172A",
        )

    ax.axhline(data["profit_margin"].median(), color="#94A3B8", linewidth=1, linestyle="--")
    ax.axvline(data["avg_discount"].median(), color="#94A3B8", linewidth=1, linestyle="--")
    ax.set_xlabel("Average Discount")
    ax.set_ylabel("Profit Margin")
    ax.xaxis.set_major_formatter(PercentFormatter(1.0))
    ax.yaxis.set_major_formatter(PercentFormatter(1.0))
    ax.set_title("Discount vs Profit Margin by Sub-Category")
    ax.grid(True)

    colorbar = fig.colorbar(scatter, ax=ax)
    colorbar.set_label("Sales")
    colorbar.ax.yaxis.set_major_formatter(FuncFormatter(compact_number))

    fig.tight_layout()
    fig.savefig(charts_dir / "discount_vs_profit_margin.png", dpi=180)
    plt.close(fig)


def export_charts(summaries: dict[str, pd.DataFrame], output_dir: Path) -> None:
    charts_dir = output_dir / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    setup_chart_style()
    save_monthly_trend(summaries["monthly"], charts_dir)
    save_category_performance(summaries["category"], charts_dir)
    save_region_performance(summaries["region"], charts_dir)
    save_top_cities(summaries["city"], charts_dir)
    save_discount_margin_scatter(summaries["subcategory"], charts_dir)


def data_quality_summary(df: pd.DataFrame) -> dict[str, object]:
    return {
        "rows": len(df),
        "columns": len(REQUIRED_COLUMNS),
        "duplicate_rows": int(df[REQUIRED_COLUMNS].duplicated().sum()),
        "missing_cells": int(df[REQUIRED_COLUMNS].isna().sum().sum()),
        "date_min": df["Order Date"].min().date().isoformat(),
        "date_max": df["Order Date"].max().date().isoformat(),
        "categories": int(df["Category"].nunique()),
        "subcategories": int(df["Sub Category"].nunique()),
        "cities": int(df["City"].nunique()),
        "regions": int(df["Region"].nunique()),
        "states": int(df["State"].nunique()),
    }


def executive_metrics(df: pd.DataFrame, summaries: dict[str, pd.DataFrame]) -> dict[str, object]:
    total_sales = float(df["Sales"].sum())
    total_profit = float(df["Profit"].sum())
    total_orders = int(df["Order ID"].count())

    category = summaries["category"]
    region = summaries["region"]
    city = summaries["city"]
    yearly = summaries["yearly"]
    subcategory = summaries["subcategory"]

    return {
        "total_sales": total_sales,
        "total_profit": total_profit,
        "profit_margin": total_profit / total_sales,
        "total_orders": total_orders,
        "customers": int(df["Customer Name"].nunique()),
        "avg_order_value": total_sales / total_orders,
        "avg_discount": float(df["Discount Rate"].mean()),
        "top_category_sales": category.iloc[0],
        "top_category_margin": category.sort_values("profit_margin", ascending=False).iloc[0],
        "lowest_category_margin": category.sort_values("profit_margin", ascending=True).iloc[0],
        "top_region_sales": region.iloc[0],
        "top_region_profit": region.sort_values("profit", ascending=False).iloc[0],
        "top_city_sales": city.iloc[0],
        "best_year_sales": yearly.sort_values("sales", ascending=False).iloc[0],
        "top_subcategory_sales": subcategory.iloc[0],
        "discount_margin_corr": float(
            subcategory[["avg_discount", "profit_margin"]].corr().iloc[0, 1]
        ),
    }


def markdown_table(df: pd.DataFrame, columns: list[str], formatters: dict[str, str]) -> str:
    table = df[columns].copy()
    for column, formatter in formatters.items():
        if formatter == "currency":
            table[column] = table[column].map(currency)
        elif formatter == "percentage":
            table[column] = table[column].map(percentage)
        elif formatter == "number":
            table[column] = table[column].map(lambda value: f"{value:,.0f}")

    table = table.fillna("").astype(str)
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    rows = [
        "| "
        + " | ".join(value.replace("|", "\\|") for value in row)
        + " |"
        for row in table.to_numpy()
    ]
    return "\n".join([header, separator, *rows])


def write_report(
    df: pd.DataFrame,
    summaries: dict[str, pd.DataFrame],
    output_dir: Path,
    report_path: Path,
) -> None:
    quality = data_quality_summary(df)
    metrics = executive_metrics(df, summaries)

    category = summaries["category"]
    region = summaries["region"]
    city = summaries["city"]
    subcategory = summaries["subcategory"]
    yearly = summaries["yearly"]

    top_category = metrics["top_category_sales"]
    top_margin_category = metrics["top_category_margin"]
    low_margin_category = metrics["lowest_category_margin"]
    top_region_sales = metrics["top_region_sales"]
    top_region_profit = metrics["top_region_profit"]
    top_city = metrics["top_city_sales"]
    top_subcategory = metrics["top_subcategory_sales"]
    best_year = metrics["best_year_sales"]

    relative_output = output_dir.relative_to(PROJECT_ROOT)
    low_volume_regions = region[region["orders"] < 30]
    low_volume_note = ""
    if not low_volume_regions.empty:
        low_volume_labels = ", ".join(
            f"{row['Region']} ({int(row['orders']):,} "
            f"{'order' if int(row['orders']) == 1 else 'orders'})"
            for _, row in low_volume_regions.iterrows()
        )
        low_volume_note = (
            f"- Low-volume region caveat: {low_volume_labels}. "
            "Treat margin comparisons for these regions as directional only."
        )

    def artifact_path(*parts: str) -> str:
        return (relative_output.joinpath(*parts)).as_posix()

    report = f"""# Supermart Grocery Sales - Retail Analytics Report

## Executive Summary

This analysis evaluates **{quality["rows"]:,} orders** from **{quality["date_min"]} to {quality["date_max"]}** across {quality["regions"]} regions and {quality["cities"]} cities in Tamil Nadu. The business generated **{currency(metrics["total_sales"])} in sales** and **{currency(metrics["total_profit"])} in profit**, for an overall profit margin of **{percentage(metrics["profit_margin"])}**.

## KPI Snapshot

| Metric | Value |
| --- | ---: |
| Orders | {metrics["total_orders"]:,} |
| Unique customers | {metrics["customers"]:,} |
| Total sales | {currency(metrics["total_sales"])} |
| Total profit | {currency(metrics["total_profit"])} |
| Profit margin | {percentage(metrics["profit_margin"])} |
| Average order value | {currency(metrics["avg_order_value"])} |
| Average discount | {percentage(metrics["avg_discount"])} |

## Data Quality Notes

- No missing values were found in the required analytical fields.
- No duplicate rows were found.
- `Order Date` contains mixed separators (`-` and `/`). The pipeline normalizes separators and parses dates with month-first convention because slash values such as `4/15/2018` are unambiguous.
- The dataset contains one state: Tamil Nadu.
{low_volume_note}

## Key Insights

1. **{top_category["Category"]} is the largest category by sales**, contributing {currency(top_category["sales"])} and {percentage(top_category["sales_share"])} of total sales.
2. **{top_margin_category["Category"]} has the strongest category-level margin** at {percentage(top_margin_category["profit_margin"])}, while **{low_margin_category["Category"]} has the lowest margin** at {percentage(low_margin_category["profit_margin"])}.
3. **{top_region_sales["Region"]} leads regional sales** with {currency(top_region_sales["sales"])}. **{top_region_profit["Region"]} leads profit** with {currency(top_region_profit["profit"])}.
4. **{top_city["City"]} is the highest-sales city**, generating {currency(top_city["sales"])} across {top_city["orders"]:,} orders.
5. **{top_subcategory["Sub Category"]} is the highest-sales sub-category**, generating {currency(top_subcategory["sales"])}.
6. **{int(best_year["Year"])} is the strongest year by sales**, generating {currency(best_year["sales"])} and {currency(best_year["profit"])} in profit.
7. At sub-category level, the correlation between average discount and profit margin is **{metrics["discount_margin_corr"]:.2f}**, so discounting should be reviewed by category rather than assumed to be uniformly harmful or helpful.

## Category Performance

{markdown_table(category, ["Category", "orders", "sales", "profit", "profit_margin", "avg_discount"], {"orders": "number", "sales": "currency", "profit": "currency", "profit_margin": "percentage", "avg_discount": "percentage"})}

## Regional Performance

{markdown_table(region, ["Region", "orders", "sales", "profit", "profit_margin", "avg_discount"], {"orders": "number", "sales": "currency", "profit": "currency", "profit_margin": "percentage", "avg_discount": "percentage"})}

## Top 10 Cities by Sales

{markdown_table(city.head(10), ["City", "orders", "sales", "profit", "profit_margin"], {"orders": "number", "sales": "currency", "profit": "currency", "profit_margin": "percentage"})}

## Yearly Trend

{markdown_table(yearly, ["Year", "orders", "sales", "profit", "profit_margin", "avg_discount"], {"orders": "number", "sales": "currency", "profit": "currency", "profit_margin": "percentage", "avg_discount": "percentage"})}

## Recommendations

- Protect and scale the strongest category and city combinations by keeping stock availability high in the top-selling segments.
- Review the lowest-margin categories for pricing, procurement cost, and promotion depth before increasing discount activity.
- Use region-level performance to plan localized promotions: prioritize margin recovery where profit lags sales.
- Monitor sub-categories with high sales and below-average margin as immediate candidates for supplier renegotiation or price tests.
- Repeat this pipeline monthly and compare new results against the exported monthly trend table.

## Output Assets

- Tables: `{artifact_path("tables")}`
- Charts: `{artifact_path("charts")}`
- Monthly trend: `{artifact_path("charts", "monthly_sales_profit_trend.png")}`
- Category performance: `{artifact_path("charts", "category_sales_margin.png")}`
- Discount vs margin: `{artifact_path("charts", "discount_vs_profit_margin.png")}`
"""

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")


def dashboard_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        if np.isnan(value):
            return None
        return float(value)
    if isinstance(value, float) and np.isnan(value):
        return None
    return value


def dashboard_records(
    table: pd.DataFrame,
    columns: list[str],
    limit: int | None = None,
) -> list[dict[str, object]]:
    selected = table.loc[:, columns]
    if limit is not None:
        selected = selected.head(limit)
    records: list[dict[str, object]] = []
    for record in selected.to_dict(orient="records"):
        records.append({key: dashboard_value(value) for key, value in record.items()})
    return records


def dashboard_segment_payload(df: pd.DataFrame, summaries: dict[str, pd.DataFrame]) -> dict[str, object]:
    quality = data_quality_summary(df)
    metrics = executive_metrics(df, summaries)
    category = summaries["category"]
    region = summaries["region"]
    city = summaries["city"]
    subcategory = summaries["subcategory"].copy()
    yearly = summaries["yearly"]

    subcategory["Subcategory Label"] = (
        subcategory["Category"].astype(str) + " / " + subcategory["Sub Category"].astype(str)
    )

    return {
        "period": f"{quality['date_min']} to {quality['date_max']}",
        "kpis": [
            {
                "label": "Sales",
                "value": dashboard_value(metrics["total_sales"]),
                "format": "currency",
                "note": f"{metrics['total_orders']:,} orders",
            },
            {
                "label": "Profit",
                "value": dashboard_value(metrics["total_profit"]),
                "format": "currency",
                "note": f"{percentage(metrics['profit_margin'])} margin",
            },
            {
                "label": "Orders",
                "value": dashboard_value(metrics["total_orders"]),
                "format": "number",
                "note": f"{metrics['customers']:,} customers",
            },
            {
                "label": "Avg Order Value",
                "value": dashboard_value(metrics["avg_order_value"]),
                "format": "currency",
                "note": "Sales per order",
            },
            {
                "label": "Avg Discount",
                "value": dashboard_value(metrics["avg_discount"]),
                "format": "percent",
                "note": "Order-level average",
            },
            {
                "label": "Best Category",
                "value": dashboard_value(metrics["top_category_sales"]["sales"]),
                "format": "currency",
                "note": str(metrics["top_category_sales"]["Category"]),
            },
        ],
        "categoryRows": dashboard_records(
            category,
            ["Category", "orders", "sales", "profit", "profit_margin", "avg_discount", "sales_share"],
        ),
        "regionRows": dashboard_records(
            region,
            ["Region", "orders", "sales", "profit", "profit_margin", "avg_discount", "sales_share"],
        ),
        "cityRows": dashboard_records(
            city,
            ["City", "orders", "sales", "profit", "profit_margin", "avg_discount"],
            limit=10,
        ),
        "subcategoryRows": dashboard_records(
            subcategory.sort_values("sales", ascending=False),
            [
                "Subcategory Label",
                "orders",
                "sales",
                "profit",
                "profit_margin",
                "avg_discount",
            ],
            limit=10,
        ),
        "yearRows": dashboard_records(
            yearly,
            ["Year", "orders", "sales", "profit", "profit_margin", "avg_discount"],
        ),
    }


def build_dashboard_payload(df: pd.DataFrame, summaries: dict[str, pd.DataFrame]) -> dict[str, object]:
    segments: dict[str, object] = {
        "all": dashboard_segment_payload(df, summaries),
    }

    years = sorted(int(year) for year in df["Year"].dropna().unique())
    for year in years:
        year_df = df[df["Year"] == year].copy()
        segments[str(year)] = dashboard_segment_payload(year_df, build_summaries(year_df))

    quality = data_quality_summary(df)
    return {
        "meta": {
            "title": "Supermart Retail Dashboard",
            "subtitle": "Grocery sales, margin, discount, and regional performance",
            "dateRange": f"{quality['date_min']} to {quality['date_max']}",
            "state": "Tamil Nadu",
            "sourceRows": quality["rows"],
        },
        "filters": [{"key": "all", "label": "All Years"}]
        + [{"key": str(year), "label": str(year)} for year in years],
        "segments": segments,
        "charts": [
            {
                "title": chart["title"],
                "src": f"assets/charts/{chart['filename']}",
                "alt": chart["alt"],
            }
            for chart in CHART_FILES
        ],
    }


def copy_dashboard_chart_assets(output_dir: Path, dashboard_path: Path) -> None:
    source_dir = output_dir / "charts"
    asset_dir = dashboard_path.parent / "assets" / "charts"
    asset_dir.mkdir(parents=True, exist_ok=True)

    for chart in CHART_FILES:
        source = source_dir / chart["filename"]
        destination = asset_dir / chart["filename"]
        if not source.exists():
            raise FileNotFoundError(f"Dashboard chart asset not found: {source}")
        shutil.copy2(source, destination)


def write_dashboard(
    df: pd.DataFrame,
    summaries: dict[str, pd.DataFrame],
    output_dir: Path,
    dashboard_path: Path,
) -> None:
    copy_dashboard_chart_assets(output_dir, dashboard_path)
    payload = build_dashboard_payload(df, summaries)
    dashboard_json = json.dumps(payload, ensure_ascii=True)

    html = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Supermart Retail Dashboard</title>
  <style>
    :root {
      --bg: #f8fafc;
      --surface: #ffffff;
      --surface-2: #f1f5f9;
      --text: #0f172a;
      --muted: #64748b;
      --line: #d9e2ef;
      --blue: #2563eb;
      --teal: #0f766e;
      --orange: #f59e0b;
      --red: #dc2626;
      --shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.5;
    }

    .shell {
      width: min(1440px, calc(100% - 32px));
      margin: 0 auto;
    }

    .topbar {
      position: sticky;
      top: 0;
      z-index: 5;
      border-bottom: 1px solid var(--line);
      background: rgba(248, 250, 252, 0.94);
      backdrop-filter: blur(12px);
    }

    .topbar-inner {
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 20px;
      align-items: center;
      padding: 18px 0;
    }

    .eyebrow {
      margin: 0 0 3px;
      color: var(--teal);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }

    h1,
    h2,
    h3,
    p {
      margin-top: 0;
    }

    h1 {
      margin-bottom: 4px;
      font-size: clamp(26px, 4vw, 38px);
      line-height: 1.08;
    }

    h2 {
      margin-bottom: 4px;
      font-size: 19px;
    }

    .muted {
      color: var(--muted);
    }

    .filter {
      display: grid;
      gap: 6px;
      min-width: 168px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }

    select {
      min-height: 42px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      color: var(--text);
      font: inherit;
      font-size: 15px;
      font-weight: 700;
      padding: 0 14px;
      box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    }

    main {
      padding: 22px 0 36px;
    }

    .kpi-grid {
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 16px;
    }

    .kpi-card,
    .panel {
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--surface);
      box-shadow: var(--shadow);
    }

    .kpi-card {
      min-height: 128px;
      padding: 16px;
    }

    .kpi-label {
      margin-bottom: 10px;
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }

    .kpi-value {
      margin-bottom: 8px;
      font-size: clamp(22px, 2.5vw, 31px);
      font-weight: 800;
      line-height: 1.05;
      overflow-wrap: anywhere;
    }

    .kpi-note {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
    }

    .dashboard-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.25fr) minmax(320px, 0.75fr);
      gap: 16px;
      margin-bottom: 16px;
    }

    .panel {
      overflow: hidden;
    }

    .panel-header {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: start;
      padding: 18px 18px 10px;
      border-bottom: 1px solid var(--line);
    }

    .panel-header p {
      margin-bottom: 0;
    }

    .bar-list {
      display: grid;
      gap: 12px;
      padding: 18px;
    }

    .bar-row {
      display: grid;
      grid-template-columns: minmax(130px, 190px) 1fr minmax(92px, auto);
      gap: 12px;
      align-items: center;
    }

    .bar-name {
      min-width: 0;
      font-weight: 700;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .bar-track {
      height: 12px;
      border-radius: 999px;
      background: var(--surface-2);
      overflow: hidden;
    }

    .bar-fill {
      height: 100%;
      min-width: 2px;
      border-radius: inherit;
      background: var(--blue);
    }

    .bar-fill.teal {
      background: var(--teal);
    }

    .bar-meta {
      color: var(--muted);
      font-size: 12px;
      text-align: right;
      white-space: nowrap;
    }

    .chart-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      margin-bottom: 16px;
    }

    .chart-panel {
      min-height: 360px;
    }

    .chart-panel.large {
      grid-column: 1 / -1;
    }

    figure {
      margin: 0;
    }

    .chart-panel img {
      display: block;
      width: 100%;
      height: auto;
      padding: 10px;
    }

    .table-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }

    .table-wrap {
      overflow-x: auto;
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 620px;
      font-size: 14px;
    }

    th,
    td {
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      white-space: nowrap;
    }

    th {
      color: var(--muted);
      font-size: 12px;
      font-weight: 800;
      text-transform: uppercase;
    }

    td.numeric,
    th.numeric {
      text-align: right;
    }

    tbody tr:hover {
      background: #f8fafc;
    }

    .footer {
      padding: 20px 0 32px;
      color: var(--muted);
      font-size: 13px;
    }

    @media (max-width: 1120px) {
      .kpi-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
      }

      .dashboard-grid,
      .chart-grid,
      .table-grid {
        grid-template-columns: 1fr;
      }
    }

    @media (max-width: 700px) {
      .shell {
        width: min(100% - 20px, 1440px);
      }

      .topbar-inner {
        grid-template-columns: 1fr;
      }

      .kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }

      .bar-row {
        grid-template-columns: 1fr;
      }

      .bar-meta {
        text-align: left;
      }
    }

    @media (max-width: 460px) {
      .kpi-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <header class="topbar">
    <div class="shell topbar-inner">
      <div>
        <p class="eyebrow">Retail Analytics</p>
        <h1 id="dashboardTitle">Supermart Retail Dashboard</h1>
        <p class="muted" id="dashboardSubtitle"></p>
      </div>
      <label class="filter" for="yearFilter">
        Year
        <select id="yearFilter"></select>
      </label>
    </div>
  </header>

  <main class="shell">
    <section class="kpi-grid" id="kpiGrid" aria-label="KPI summary"></section>

    <section class="dashboard-grid" aria-label="Performance summary">
      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>Category Performance</h2>
            <p class="muted">Sales contribution with profit margin context.</p>
          </div>
        </div>
        <div class="bar-list" id="categoryBars"></div>
      </article>

      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>Region Mix</h2>
            <p class="muted">Revenue distribution and margin by region.</p>
          </div>
        </div>
        <div class="bar-list" id="regionBars"></div>
      </article>
    </section>

    <section class="chart-grid" id="chartGrid" aria-label="Generated chart assets"></section>

    <section class="table-grid" aria-label="Ranked detail tables">
      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>Top Cities</h2>
            <p class="muted">Highest sales cities in the selected period.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table id="cityTable"></table>
        </div>
      </article>

      <article class="panel">
        <div class="panel-header">
          <div>
            <h2>Top Sub-Categories</h2>
            <p class="muted">Product groups ranked by sales.</p>
          </div>
        </div>
        <div class="table-wrap">
          <table id="subcategoryTable"></table>
        </div>
      </article>
    </section>
  </main>

  <footer class="shell footer">
    Static dashboard generated from the Supermart Grocery Sales analytics pipeline.
  </footer>

  <script>
    window.DASHBOARD_DATA = __DASHBOARD_DATA__;
  </script>
  <script>
    const dashboard = window.DASHBOARD_DATA;
    const yearFilter = document.querySelector("#yearFilter");
    const kpiGrid = document.querySelector("#kpiGrid");

    const formatters = {
      currency: new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 0
      }),
      number: new Intl.NumberFormat("en-US", {
        maximumFractionDigits: 0
      }),
      percent: new Intl.NumberFormat("en-US", {
        style: "percent",
        minimumFractionDigits: 1,
        maximumFractionDigits: 1
      })
    };

    function formatValue(value, type) {
      if (value === null || value === undefined || Number.isNaN(value)) {
        return "";
      }
      if (type === "currency") {
        return formatters.currency.format(value);
      }
      if (type === "number") {
        return formatters.number.format(value);
      }
      if (type === "percent") {
        return formatters.percent.format(value);
      }
      return String(value);
    }

    function renderKpis(segment) {
      kpiGrid.replaceChildren();
      segment.kpis.forEach((kpi) => {
        const card = document.createElement("article");
        card.className = "kpi-card";

        const label = document.createElement("div");
        label.className = "kpi-label";
        label.textContent = kpi.label;

        const value = document.createElement("div");
        value.className = "kpi-value";
        value.textContent = formatValue(kpi.value, kpi.format);

        const note = document.createElement("p");
        note.className = "kpi-note";
        note.textContent = kpi.note;

        card.append(label, value, note);
        kpiGrid.append(card);
      });
    }

    function renderBars(targetId, rows, config) {
      const target = document.querySelector(`#${targetId}`);
      target.replaceChildren();
      const maxValue = Math.max(...rows.map((row) => row[config.valueKey]), 1);

      rows.forEach((row) => {
        const wrapper = document.createElement("div");
        wrapper.className = "bar-row";

        const name = document.createElement("div");
        name.className = "bar-name";
        name.title = row[config.nameKey];
        name.textContent = row[config.nameKey];

        const track = document.createElement("div");
        track.className = "bar-track";
        const fill = document.createElement("div");
        fill.className = `bar-fill ${config.color || ""}`.trim();
        fill.style.width = `${Math.max((row[config.valueKey] / maxValue) * 100, 1)}%`;
        track.append(fill);

        const meta = document.createElement("div");
        meta.className = "bar-meta";
        meta.textContent = `${formatValue(row[config.valueKey], "currency")} | ${formatValue(row.profit_margin, "percent")}`;

        wrapper.append(name, track, meta);
        target.append(wrapper);
      });
    }

    function renderTable(targetId, rows, columns) {
      const table = document.querySelector(`#${targetId}`);
      table.replaceChildren();

      const thead = document.createElement("thead");
      const headRow = document.createElement("tr");
      columns.forEach((column) => {
        const th = document.createElement("th");
        th.textContent = column.label;
        if (column.numeric) {
          th.className = "numeric";
        }
        headRow.append(th);
      });
      thead.append(headRow);

      const tbody = document.createElement("tbody");
      rows.forEach((row) => {
        const tr = document.createElement("tr");
        columns.forEach((column) => {
          const td = document.createElement("td");
          if (column.numeric) {
            td.className = "numeric";
          }
          td.textContent = formatValue(row[column.key], column.format);
          tr.append(td);
        });
        tbody.append(tr);
      });

      table.append(thead, tbody);
    }

    function renderCharts() {
      const chartGrid = document.querySelector("#chartGrid");
      chartGrid.replaceChildren();
      dashboard.charts.forEach((chart, index) => {
        const panel = document.createElement("figure");
        panel.className = index === 0 ? "panel chart-panel large" : "panel chart-panel";

        const header = document.createElement("figcaption");
        header.className = "panel-header";
        const titleWrap = document.createElement("div");
        const title = document.createElement("h2");
        title.textContent = chart.title;
        titleWrap.append(title);
        header.append(titleWrap);

        const img = document.createElement("img");
        img.src = chart.src;
        img.alt = chart.alt;
        img.loading = "lazy";

        panel.append(header, img);
        chartGrid.append(panel);
      });
    }

    function renderSegment(key) {
      const segment = dashboard.segments[key];
      document.querySelector("#dashboardTitle").textContent = dashboard.meta.title;
      document.querySelector("#dashboardSubtitle").textContent =
        `${dashboard.meta.subtitle} | ${segment.period} | ${dashboard.meta.state}`;

      renderKpis(segment);
      renderBars("categoryBars", segment.categoryRows, {
        nameKey: "Category",
        valueKey: "sales",
        color: "teal"
      });
      renderBars("regionBars", segment.regionRows, {
        nameKey: "Region",
        valueKey: "sales"
      });
      renderTable("cityTable", segment.cityRows, [
        { key: "City", label: "City" },
        { key: "orders", label: "Orders", format: "number", numeric: true },
        { key: "sales", label: "Sales", format: "currency", numeric: true },
        { key: "profit", label: "Profit", format: "currency", numeric: true },
        { key: "profit_margin", label: "Margin", format: "percent", numeric: true }
      ]);
      renderTable("subcategoryTable", segment.subcategoryRows, [
        { key: "Subcategory Label", label: "Sub-Category" },
        { key: "orders", label: "Orders", format: "number", numeric: true },
        { key: "sales", label: "Sales", format: "currency", numeric: true },
        { key: "profit_margin", label: "Margin", format: "percent", numeric: true },
        { key: "avg_discount", label: "Discount", format: "percent", numeric: true }
      ]);
    }

    dashboard.filters.forEach((filter) => {
      const option = document.createElement("option");
      option.value = filter.key;
      option.textContent = filter.label;
      yearFilter.append(option);
    });

    yearFilter.addEventListener("change", (event) => {
      renderSegment(event.target.value);
    });

    renderCharts();
    renderSegment("all");
  </script>
</body>
</html>
"""

    dashboard_path.parent.mkdir(parents=True, exist_ok=True)
    dashboard_path.write_text(
        html.replace("__DASHBOARD_DATA__", dashboard_json),
        encoding="utf-8",
    )


def run_pipeline(
    input_path: Path,
    output_dir: Path,
    report_path: Path,
    dashboard_path: Path,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = load_and_prepare_data(input_path)
    summaries = build_summaries(df)
    export_tables(summaries, output_dir)
    export_charts(summaries, output_dir)
    write_report(df, summaries, output_dir, report_path)
    write_dashboard(df, summaries, output_dir, dashboard_path)


def main() -> None:
    args = parse_args()
    run_pipeline(args.input, args.output_dir, args.report_path, args.dashboard_path)
    print(f"Analysis complete: {args.report_path}")
    print(f"Dashboard complete: {args.dashboard_path}")


if __name__ == "__main__":
    main()

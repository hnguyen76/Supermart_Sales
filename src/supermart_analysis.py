"""Retail analytics pipeline for the Supermart Grocery Sales dataset.

The script validates the raw CSV, creates analysis-ready summaries, exports
chart assets, and writes a Markdown business report.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import FuncFormatter, PercentFormatter


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "Supermart Grocery Sales - Retail Analytics Dataset.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_REPORT_PATH = PROJECT_ROOT / "reports" / "supermart_sales_analysis.md"

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


def run_pipeline(input_path: Path, output_dir: Path, report_path: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    df = load_and_prepare_data(input_path)
    summaries = build_summaries(df)
    export_tables(summaries, output_dir)
    export_charts(summaries, output_dir)
    write_report(df, summaries, output_dir, report_path)


def main() -> None:
    args = parse_args()
    run_pipeline(args.input, args.output_dir, args.report_path)
    print(f"Analysis complete: {args.report_path}")


if __name__ == "__main__":
    main()

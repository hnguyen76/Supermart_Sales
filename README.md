# Supermart Grocery Sales - Retail Analytics

Professional retail analytics project built from the Supermart Grocery Sales dataset. The project validates the raw CSV, creates reusable summary tables, generates executive charts, writes a business-ready Markdown report, and builds a static HTML dashboard.

## Business Objective

Identify sales, profit, discount, category, region, city, and time-based patterns that can support merchandising, promotion, and regional performance decisions.

## Repository Structure

```text
.
|-- Supermart Grocery Sales - Retail Analytics Dataset.csv
|-- dashboard/
|   `-- index.html
|-- src/
|   |-- __init__.py
|   `-- supermart_analysis.py
|-- docs/
|   `-- data_dictionary.md
|-- reports/
|   `-- supermart_sales_analysis.md
|-- outputs/
|   |-- charts/
|   `-- tables/
|-- requirements.txt
`-- README.md
```

## How to Run

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python src/supermart_analysis.py
```

The pipeline writes:

- Static dashboard to `dashboard/index.html`
- Dashboard chart assets to `dashboard/assets/charts/`
- Summary CSV files to `outputs/tables/`
- Chart PNG files to `outputs/charts/`
- Business report to `reports/supermart_sales_analysis.md`

## Dashboard Layer

Open `dashboard/index.html` in a browser after running the pipeline. The dashboard includes KPI cards, a year filter, category and region performance bars, generated chart assets, and ranked city/sub-category tables. The chart images are copied into `dashboard/assets/charts/` so the dashboard works even when a browser preview serves only the `dashboard/` folder.

## Professional Report Layer

The repo also includes a Quarto-ready report source:

- [Quarto report source](reports/supermart_sales_report.qmd)

After installing Quarto CLI, render it with:

```bash
quarto render reports/supermart_sales_report.qmd
```

This creates a polished HTML report, and the same source can also be rendered to PDF when a LaTeX engine is available.

## Analysis Scope

- Data quality checks: required columns, missing values, duplicate rows, numeric conversion, date parsing.
- Executive KPIs: total sales, total profit, profit margin, average order value, average discount, customers, and orders.
- Performance cuts: category, sub-category, region, city, monthly trend, and yearly trend.
- Visuals: monthly sales/profit trend, category margin overlay, regional performance, top cities, and discount-vs-margin bubble chart.

## Key Files

- [Dashboard](dashboard/index.html)
- [Analysis script](src/supermart_analysis.py)
- [Generated report](reports/supermart_sales_analysis.md)
- [Quarto report source](reports/supermart_sales_report.qmd)
- [Data dictionary](docs/data_dictionary.md)

## Notes

The raw `Order Date` column contains mixed separators (`-` and `/`). The pipeline normalizes separators and parses dates with month-first convention because slash values such as `4/15/2018` are unambiguous.

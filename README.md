# Supermart Grocery Sales - Retail Analytics

Professional retail analytics project built from the Supermart Grocery Sales dataset. The project validates the raw CSV, creates reusable summary tables, generates executive charts, and writes a business-ready Markdown report.

## Business Objective

Identify sales, profit, discount, category, region, city, and time-based patterns that can support merchandising, promotion, and regional performance decisions.

## Repository Structure

```text
.
├── Supermart Grocery Sales - Retail Analytics Dataset.csv
├── src/
│   └── supermart_analysis.py
├── docs/
│   └── data_dictionary.md
├── reports/
│   └── supermart_sales_analysis.md
├── outputs/
│   ├── charts/
│   └── tables/
├── requirements.txt
└── README.md
```

## How to Run

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python src/supermart_analysis.py
```

The pipeline writes:

- Summary CSV files to `outputs/tables/`
- Chart PNG files to `outputs/charts/`
- Business report to `reports/supermart_sales_analysis.md`

## Analysis Scope

- Data quality checks: required columns, missing values, duplicate rows, numeric conversion, date parsing.
- Executive KPIs: total sales, total profit, profit margin, average order value, average discount, customers, and orders.
- Performance cuts: category, sub-category, region, city, monthly trend, and yearly trend.
- Visuals: monthly sales/profit trend, category margin overlay, regional performance, top cities, and discount-vs-margin bubble chart.

## Key Files

- [Analysis script](src/supermart_analysis.py)
- [Generated report](reports/supermart_sales_analysis.md)
- [Data dictionary](docs/data_dictionary.md)

## Notes

The raw `Order Date` column contains mixed separators (`-` and `/`). The pipeline normalizes separators and parses dates with month-first convention because slash values such as `4/15/2018` are unambiguous.

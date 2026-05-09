# Supermart Grocery Sales - Retail Analytics Report

## Executive Summary

This analysis evaluates **9,994 orders** from **2015-01-03 to 2018-12-30** across 5 regions and 24 cities in Tamil Nadu. The business generated **$14,956,982 in sales** and **$3,747,121 in profit**, for an overall profit margin of **25.1%**.

## KPI Snapshot

| Metric | Value |
| --- | ---: |
| Orders | 9,994 |
| Unique customers | 50 |
| Total sales | $14,956,982 |
| Total profit | $3,747,121 |
| Profit margin | 25.1% |
| Average order value | $1,497 |
| Average discount | 22.7% |

## Data Quality Notes

- No missing values were found in the required analytical fields.
- No duplicate rows were found.
- `Order Date` contains mixed separators (`-` and `/`). The pipeline normalizes separators and parses dates with month-first convention because slash values such as `4/15/2018` are unambiguous.
- The dataset contains one state: Tamil Nadu.
- Low-volume region caveat: North (1 order). Treat margin comparisons for these regions as directional only.

## Key Insights

1. **Eggs, Meat & Fish is the largest category by sales**, contributing $2,267,401 and 15.2% of total sales.
2. **Snacks has the strongest category-level margin** at 25.4%, while **Oil & Masala has the lowest margin** at 24.4%.
3. **West leads regional sales** with $4,798,743. **West leads profit** with $1,192,005.
4. **Kanyakumari is the highest-sales city**, generating $706,764 across 459 orders.
5. **Health Drinks is the highest-sales sub-category**, generating $1,051,439.
6. **2018 is the strongest year by sales**, generating $4,977,512 and $1,244,183 in profit.
7. At sub-category level, the correlation between average discount and profit margin is **0.32**, so discounting should be reviewed by category rather than assumed to be uniformly harmful or helpful.

## Category Performance

| Category | orders | sales | profit | profit_margin | avg_discount |
| --- | --- | --- | --- | --- | --- |
| Eggs, Meat & Fish | 1,490 | $2,267,401 | $567,357 | 25.0% | 22.8% |
| Snacks | 1,514 | $2,237,546 | $568,179 | 25.4% | 22.2% |
| Food Grains | 1,398 | $2,115,272 | $529,163 | 25.0% | 22.9% |
| Bakery | 1,413 | $2,112,281 | $528,521 | 25.0% | 22.5% |
| Fruits & Veggies | 1,418 | $2,100,727 | $530,400 | 25.2% | 22.9% |
| Beverages | 1,400 | $2,085,313 | $525,606 | 25.2% | 23.0% |
| Oil & Masala | 1,361 | $2,038,442 | $497,895 | 24.4% | 22.5% |

## Regional Performance

| Region | orders | sales | profit | profit_margin | avg_discount |
| --- | --- | --- | --- | --- | --- |
| West | 3,203 | $4,798,743 | $1,192,005 | 24.8% | 22.5% |
| East | 2,848 | $4,248,368 | $1,074,346 | 25.3% | 22.8% |
| Central | 2,323 | $3,468,156 | $856,807 | 24.7% | 22.9% |
| South | 1,619 | $2,440,461 | $623,563 | 25.6% | 22.7% |
| North | 1 | $1,254 | $401 | 32.0% | 12.0% |

## Top 10 Cities by Sales

| City | orders | sales | profit | profit_margin |
| --- | --- | --- | --- | --- |
| Kanyakumari | 459 | $706,764 | $172,218 | 24.4% |
| Vellore | 435 | $676,550 | $174,073 | 25.7% |
| Bodi | 442 | $667,177 | $173,655 | 26.0% |
| Tirunelveli | 446 | $659,812 | $165,169 | 25.0% |
| Perambalur | 434 | $659,738 | $171,132 | 25.9% |
| Salem | 431 | $657,093 | $160,899 | 24.5% |
| Pudukottai | 430 | $653,179 | $164,073 | 25.1% |
| Tenkasi | 432 | $643,652 | $156,231 | 24.3% |
| Karur | 430 | $642,273 | $169,306 | 26.4% |
| Krishnagiri | 440 | $637,273 | $160,477 | 25.2% |

## Yearly Trend

| Year | orders | sales | profit | profit_margin | avg_discount |
| --- | --- | --- | --- | --- | --- |
| 2015 | 1,993 | $2,975,599 | $752,529 | 25.3% | 22.9% |
| 2016 | 2,102 | $3,131,959 | $797,193 | 25.5% | 22.7% |
| 2017 | 2,587 | $3,871,912 | $953,216 | 24.6% | 22.7% |
| 2018 | 3,312 | $4,977,512 | $1,244,183 | 25.0% | 22.5% |

## Recommendations

- Protect and scale the strongest category and city combinations by keeping stock availability high in the top-selling segments.
- Review the lowest-margin categories for pricing, procurement cost, and promotion depth before increasing discount activity.
- Use region-level performance to plan localized promotions: prioritize margin recovery where profit lags sales.
- Monitor sub-categories with high sales and below-average margin as immediate candidates for supplier renegotiation or price tests.
- Repeat this pipeline monthly and compare new results against the exported monthly trend table.

## Output Assets

- Tables: `outputs/tables`
- Charts: `outputs/charts`
- Monthly trend: `outputs/charts/monthly_sales_profit_trend.png`
- Category performance: `outputs/charts/category_sales_margin.png`
- Discount vs margin: `outputs/charts/discount_vs_profit_margin.png`

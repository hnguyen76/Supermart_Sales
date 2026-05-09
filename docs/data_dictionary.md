# Data Dictionary

| Column | Type | Description |
| --- | --- | --- |
| `Order ID` | String | Unique order identifier in the source file. |
| `Customer Name` | String | Customer name associated with the order. |
| `Category` | String | Product category. |
| `Sub Category` | String | More granular product group within category. |
| `City` | String | City where the order was placed. |
| `Order Date` | Date | Original order date. The pipeline normalizes mixed `-` and `/` separators and parses month-first dates. |
| `Region` | String | Sales region. |
| `Sales` | Numeric | Order sales amount. |
| `Discount` | Numeric | Discount rate applied to the order. |
| `Profit` | Numeric | Profit amount for the order. |
| `State` | String | State associated with the order. |

## Derived Fields

| Field | Description |
| --- | --- |
| `Year` | Calendar year extracted from `Order Date`. |
| `Month` | Month start date used for trend aggregation. |
| `Month Label` | `YYYY-MM` formatted month label. |
| `Profit Margin` | `Profit / Sales`. |
| `Discount Rate` | Copy of `Discount` with business-friendly naming. |

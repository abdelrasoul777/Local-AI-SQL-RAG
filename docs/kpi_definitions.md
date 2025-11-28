# KPI Definitions

## AOV (Average Order Value)
Formula: SUM(UnitPrice * Quantity * (1 - Discount)) / COUNT(DISTINCT OrderID)

## Gross Margin
Formula: (Revenue - Cost) / Revenue
Note: Cost of Goods Sold (COGS) = 0.7 * UnitPrice (when cost field not available)

## Revenue
Formula: SUM(UnitPrice * Quantity * (1 - Discount))

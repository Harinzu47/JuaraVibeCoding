from typing import Any


class FinancialCalculator:
    """Handles deterministic financial calculations (avoiding LLM math hallucinations)."""

    @staticmethod
    def calculate_morning_metrics(
        items: list[dict[str, Any]],
        servings: int | None,
        existing_total: int = 0
    ) -> dict[str, int]:
        """
        Calculates Total Spending and COGS for the morning phase based on extracted items.
        Returns total_spending, used_capital, and cogs_per_unit.
        """
        # Sum all the item prices (assuming each item dictionary has a 'price' key)
        new_spending = sum(item.get("price", 0) for item in items)
        total_spending = existing_total + new_spending

        # In this simple model, all spent capital is considered "used" for the batch
        used_capital = total_spending

        # Calculate COGS per unit if servings is provided and valid
        cogs_per_unit = 0
        if servings is not None and servings > 0:
            cogs_per_unit = used_capital // servings

        return {
            "total_spending": total_spending,
            "used_capital": used_capital,
            "cogs_per_unit": cogs_per_unit,
        }

    @staticmethod
    def calculate_evening_metrics(
        units_sold: int | None,
        selling_price: int | None,
        cogs_per_unit: int,
        total_spending: int,
    ) -> dict[str, int | bool]:
        """
        Calculates revenue, net profit, and break-even status for the evening sales phase.
        """
        # If units or price aren't fully provided, we can't calculate everything yet
        if units_sold is None or selling_price is None:
            return {
                "total_revenue": 0,
                "net_profit": 0,
                "portions_sold": units_sold or 0,
                "selling_price": selling_price or 0,
                "break_even": False,
            }

        total_revenue = units_sold * selling_price
        
        # Net profit = Revenue - Total Cost of Goods Sold (for the units sold)
        # Note: Depending on business logic, sometimes profit is revenue - total_spending. 
        # But standard COGS logic is profit = revenue - (units_sold * cogs_per_unit)
        total_cogs = units_sold * cogs_per_unit
        net_profit = total_revenue - total_cogs

        # Break even is usually when total_revenue >= total_spending 
        break_even = total_revenue >= total_spending

        return {
            "total_revenue": total_revenue,
            "net_profit": net_profit,
            "portions_sold": units_sold,
            "selling_price": selling_price,
            "break_even": break_even,
        }

    @staticmethod
    def apply_spending_correction(
        current_total_spending: int,
        current_cogs_per_unit: int,
        portions_made: int,
        old_price: int,
        new_price: int,
    ) -> tuple[int, int, int]:
        """
        Calculates the updated total spending, used capital, and COGS after correcting an item's price.
        """
        diff = new_price - old_price
        new_total_spending = max(0, current_total_spending + diff)
        new_used_capital = new_total_spending  # Simplified model where used = total

        if portions_made > 0:
            new_cogs = new_used_capital // portions_made
        else:
            new_cogs = current_cogs_per_unit

        return new_total_spending, new_used_capital, new_cogs

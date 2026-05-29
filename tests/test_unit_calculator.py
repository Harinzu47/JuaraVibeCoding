from app.services.calculator import FinancialCalculator


def test_morning_metrics_normal():
    items = [{"name": "Ayam", "price": 50000}, {"name": "Beras", "price": 30000}]
    metrics = FinancialCalculator.calculate_morning_metrics(items, servings=10, existing_total=0)
    
    assert metrics["total_spending"] == 80000
    assert metrics["used_capital"] == 80000
    assert metrics["cogs_per_unit"] == 8000


def test_morning_metrics_with_existing_total():
    items = [{"name": "Sayur", "price": 20000}]
    metrics = FinancialCalculator.calculate_morning_metrics(items, servings=10, existing_total=80000)
    
    assert metrics["total_spending"] == 100000
    assert metrics["used_capital"] == 100000
    assert metrics["cogs_per_unit"] == 10000


def test_morning_metrics_zero_servings():
    items = [{"name": "Ayam", "price": 50000}]
    metrics = FinancialCalculator.calculate_morning_metrics(items, servings=0, existing_total=0)
    
    assert metrics["total_spending"] == 50000
    assert metrics["used_capital"] == 50000
    assert metrics["cogs_per_unit"] == 0  # No servings yet


def test_evening_metrics_normal():
    metrics = FinancialCalculator.calculate_evening_metrics(
        units_sold=8,
        selling_price=15000,
        cogs_per_unit=10000,
        total_spending=100000
    )
    
    assert metrics["total_revenue"] == 120000
    assert metrics["net_profit"] == 40000  # 120k - (8 * 10k)
    assert metrics["portions_sold"] == 8
    assert metrics["selling_price"] == 15000
    assert metrics["break_even"] is True  # 120k >= 100k


def test_evening_metrics_loss():
    metrics = FinancialCalculator.calculate_evening_metrics(
        units_sold=5,
        selling_price=15000,
        cogs_per_unit=10000,
        total_spending=100000
    )
    
    assert metrics["total_revenue"] == 75000
    assert metrics["net_profit"] == 25000  # 75k - (5 * 10k) - wait, net operational profit on items sold is 25k. 
    # BUT total spending was 100k, so overall they didn't break even.
    assert metrics["portions_sold"] == 5
    assert metrics["selling_price"] == 15000
    assert metrics["break_even"] is False  # 75k < 100k


def test_spending_correction():
    total, used, cogs = FinancialCalculator.apply_spending_correction(
        current_total_spending=100000,
        current_cogs_per_unit=10000,
        portions_made=10,
        old_price=20000,
        new_price=10000
    )
    
    # Decreased spending by 10k
    assert total == 90000
    assert used == 90000
    assert cogs == 9000

from app.api.v1.chat import calculate_morning_metrics


def test_morning_metrics_normal():
    total, modal, cogs, phase = calculate_morning_metrics(
        raw_total_spending=100000,
        raw_used_capital=80000,
        raw_cogs_per_unit=0,
        current_total_spending=0,
        current_cogs_per_unit=0,
    )
    assert total == 100000
    assert modal == 80000
    assert cogs == 0
    assert phase == "MORNING_COSTING"


def test_morning_metrics_negative_clamping():
    total, modal, cogs, phase = calculate_morning_metrics(
        raw_total_spending=-50000,
        raw_used_capital=-10000,
        raw_cogs_per_unit=-5000,
        current_total_spending=10000,
        current_cogs_per_unit=0,
    )
    assert total == 0
    assert modal == 0
    assert cogs == 0
    assert phase == "MORNING_COSTING"


def test_morning_metrics_modal_terpakai_exceeds_total():
    # If used capital exceeds total spending, clamp it to total spending
    total, modal, cogs, phase = calculate_morning_metrics(
        raw_total_spending=50000,
        raw_used_capital=60000,
        raw_cogs_per_unit=0,
        current_total_spending=0,
        current_cogs_per_unit=0,
    )
    assert total == 50000
    assert modal == 50000
    assert cogs == 0


def test_morning_metrics_fase_transition():
    # If cogs > 0, phase must transition to EVENING_SALES
    total, modal, cogs, phase = calculate_morning_metrics(
        raw_total_spending=100000,
        raw_used_capital=100000,
        raw_cogs_per_unit=10000,
        current_total_spending=0,
        current_cogs_per_unit=0,
    )
    assert cogs == 10000
    assert phase == "EVENING_SALES"

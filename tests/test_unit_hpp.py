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


def test_morning_metrics_negative_values_preserve_current_state():
    # Negative values from Gemini are treated as "no useful data" — preserve current_state
    total, modal, cogs, phase = calculate_morning_metrics(
        raw_total_spending=-50000,
        raw_used_capital=-10000,
        raw_cogs_per_unit=-5000,
        current_total_spending=10000,
        current_cogs_per_unit=0,
    )
    # Negative raw values do not override, so total stays at current_total_spending=10000
    assert total == 10000
    assert modal == 0
    assert cogs == 0
    assert phase == "MORNING_COSTING"


def test_morning_metrics_zero_from_gemini_preserves_current_state():
    # If Gemini returns 0 (NEED_CLARIFICATION case), current state is preserved
    total, modal, cogs, phase = calculate_morning_metrics(
        raw_total_spending=0,
        raw_used_capital=0,
        raw_cogs_per_unit=0,
        current_total_spending=50000,
        current_cogs_per_unit=5000,
    )
    # Zeros from Gemini must NOT wipe out the real accumulated state
    assert total == 50000
    assert modal == 0
    assert cogs == 5000
    assert phase == "EVENING_SALES"  # Because current_cogs_per_unit=5000 > 0


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



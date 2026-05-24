from app.api.v1.chat import apply_spending_correction


def test_spending_correction_normal():
    # Initial spending 100k, COGS 10k, portions 10
    # Correction: old price 20k, new price 15k
    # Diff: -5k -> new total 95k
    # new cogs: 95k / 10 = 9.5k
    new_total, new_cogs = apply_spending_correction(
        current_total_spending=100000,
        current_cogs_per_unit=10000,
        portions_made=10,
        old_price=20000,
        new_price=15000,
    )
    assert new_total == 95000
    assert new_cogs == 9500


def test_spending_correction_increase():
    # Initial spending 100k, COGS 10k, portions 10
    # Correction: old price 20k, new price 30k
    # Diff: +10k -> new total 110k
    # new cogs: 110k / 10 = 11k
    new_total, new_cogs = apply_spending_correction(
        current_total_spending=100000,
        current_cogs_per_unit=10000,
        portions_made=10,
        old_price=20000,
        new_price=30000,
    )
    assert new_total == 110000
    assert new_cogs == 11000


def test_spending_correction_clamped_at_zero():
    # Correction creates negative diff larger than current total spending
    new_total, new_cogs = apply_spending_correction(
        current_total_spending=10000,
        current_cogs_per_unit=1000,
        portions_made=10,
        old_price=20000,
        new_price=0,
    )
    assert new_total == 0
    assert new_cogs == 0


def test_spending_correction_portions_zero():
    # Portions made = 0, old COGS must be preserved
    new_total, new_cogs = apply_spending_correction(
        current_total_spending=100000,
        current_cogs_per_unit=0,
        portions_made=0,
        old_price=20000,
        new_price=30000,
    )
    assert new_total == 110000
    assert new_cogs == 0

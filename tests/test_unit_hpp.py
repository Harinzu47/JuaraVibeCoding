import pytest
from main import calculate_pagi_metrics

def test_pagi_metrics_normal():
    total, modal, hpp, fase = calculate_pagi_metrics(
        raw_total_belanja=100000,
        raw_modal_terpakai=80000,
        raw_hpp_unit=0,
        current_total_belanja=0,
        current_hpp_unit=0
    )
    assert total == 100000
    assert modal == 80000
    assert hpp == 0
    assert fase == "PAGI_COSTING"

def test_pagi_metrics_negative_clamping():
    total, modal, hpp, fase = calculate_pagi_metrics(
        raw_total_belanja=-50000,
        raw_modal_terpakai=-10000,
        raw_hpp_unit=-5000,
        current_total_belanja=10000,
        current_hpp_unit=0
    )
    assert total == 0
    assert modal == 0
    assert hpp == 0
    assert fase == "PAGI_COSTING"

def test_pagi_metrics_modal_terpakai_exceeds_total():
    # Jika modal terpakai diinput melebihi total belanja, maka harus diclamp ke total_belanja
    total, modal, hpp, fase = calculate_pagi_metrics(
        raw_total_belanja=50000,
        raw_modal_terpakai=60000,
        raw_hpp_unit=0,
        current_total_belanja=0,
        current_hpp_unit=0
    )
    assert total == 50000
    assert modal == 50000
    assert hpp == 0

def test_pagi_metrics_fase_transition():
    # Jika hpp_unit > 0, fase harus berubah ke SORE_REVENUE
    total, modal, hpp, fase = calculate_pagi_metrics(
        raw_total_belanja=100000,
        raw_modal_terpakai=100000,
        raw_hpp_unit=10000,
        current_total_belanja=0,
        current_hpp_unit=0
    )
    assert hpp == 10000
    assert fase == "SORE_REVENUE"

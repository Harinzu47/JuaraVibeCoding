import pytest
from main import apply_koreksi_belanja

def test_koreksi_belanja_normal():
    # Belanja awal 100k, hpp 10k, porsi 10
    # Koreksi: harga lama 20k, harga baru 15k
    # Selisih: -5k -> new total 95k
    # new hpp: 95k / 10 = 9.5k -> 9k (integer division)
    new_total, new_hpp = apply_koreksi_belanja(
        current_total_belanja=100000,
        current_hpp_unit=10000,
        porsi_dibuat=10,
        harga_lama=20000,
        harga_baru=15000
    )
    assert new_total == 95000
    assert new_hpp == 9500

def test_koreksi_belanja_kenaikan():
    # Belanja awal 100k, hpp 10k, porsi 10
    # Koreksi: harga lama 20k, harga baru 30k
    # Selisih: +10k -> new total 110k
    # new hpp: 110k / 10 = 11k
    new_total, new_hpp = apply_koreksi_belanja(
        current_total_belanja=100000,
        current_hpp_unit=10000,
        porsi_dibuat=10,
        harga_lama=20000,
        harga_baru=30000
    )
    assert new_total == 110000
    assert new_hpp == 11000

def test_koreksi_belanja_tidak_bisa_negatif():
    # Koreksi membuat selisih lebih besar negatif dari total_belanja
    new_total, new_hpp = apply_koreksi_belanja(
        current_total_belanja=10000,
        current_hpp_unit=1000,
        porsi_dibuat=10,
        harga_lama=20000,
        harga_baru=0
    )
    assert new_total == 0
    assert new_hpp == 0

def test_koreksi_belanja_porsi_belum_dicatat():
    # Porsi dibuat = 0, HPP lama harus dipertahankan
    new_total, new_hpp = apply_koreksi_belanja(
        current_total_belanja=100000,
        current_hpp_unit=0,
        porsi_dibuat=0,
        harga_lama=20000,
        harga_baru=30000
    )
    assert new_total == 110000
    assert new_hpp == 0

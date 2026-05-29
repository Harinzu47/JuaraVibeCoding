# AturModal Design System (Warm-Minimalist)

Dokumen ini mendefinisikan panduan visual, token desain, dan implementasi komponen UI untuk **AturModal** berbasis Streamlit. Referensi ini dibuat agar tampilan aplikasi konsisten dengan rancangan desain Stitch AI.

---

## 1. Konsep & Kepribadian Brand
*   **Creative North Star:** "The Encouraging Mentor" — Asisten keuangan yang cerdas namun hangat, bersahabat untuk Ibu Rumah Tangga dan pelaku UMKM kuliner.
*   **Gaya Visual:** **Modern-Warm Minimalist**. Menghindari warna biru/abu-abu finansial yang dingin, digantikan dengan warna putih gading hangat, oranye hangat, dan toska guna meredakan kecemasan finansial (math anxiety).

---

## 2. Token Desain (Design Tokens)

### A. Palet Warna (Color Palette)
| Token | Nilai Hex | Penggunaan |
| :--- | :--- | :--- |
| **Primary (Amber/Orange)** | `#9d4300` | Warna utama untuk teks utama, tombol primer, dan identitas brand. |
| **Primary Container** | `#f97316` | Warna hover/aktif, aksen oranye terang. |
| **On Primary** | `#ffffff` | Teks di atas warna primary. |
| **Secondary (Teal/Positive)**| `#006a61` | Digunakan untuk metrik laba bersih, pertumbuhan modal, dan status sukses. |
| **Secondary Container** | `#86f2e4` | Background untuk status positif atau badge pertumbuhan. |
| **Background (Warm White)** | `#fff8f5` | Dasar halaman utama (Soft Eggshell) untuk mengurangi ketegangan mata. |
| **Surface Container (Warm Gray)**| `#f6ece6` | Warna dasar Sidebar kiri dan elemen container sekunder. |
| **Surface Container Highest** | `#eae1da` | Latar belakang untuk gelembung chat Asisten. |
| **On Surface (Dark Text)** | `#1f1b17` | Warna teks utama (bukan hitam pekat untuk kesan lebih lembut). |
| **On Surface Variant (Muted)** | `#584237` | Teks sekunder, label metrik, dan deskripsi. |
| **Outline Variant (Border)** | `#e0c0b1` | Garis batas tipis yang sangat halus. |

### B. Bentuk & Kelengkungan (Shapes & Radius)
*   **Kelengkungan Standar (Border Radius):**
    *   Input Fields & Tombol Kecil: `0.5rem` (`8px` / `rounded-lg`)
    *   Card Metrik & Panel Info: `0.75rem` (`12px` / `rounded-xl`)
    *   Gelembung Chat (Chat Bubbles): `1.0rem` (`16px` / `rounded-2xl`)
    *   Tombol Kirim & Badge Status: `9999px` (`rounded-full`)

### C. Tipografi (Typography)
*   **Font Utama:** `Plus Jakarta Sans` (atau fallback `sans-serif`)
*   **Skala:**
    *   **Headline-LG:** `32px` (Bold) - Untuk nama aplikasi utama.
    *   **Headline-MD:** `24px` (Semi-Bold) - Angka nominal uang di metrik.
    *   **Body-MD:** `16px` (Regular, Line Height 1.5) - Teks obrolan.
    *   **Label-SM:** `12px` (Semi-Bold) - Teks penunjuk waktu/label kecil.

---

## 3. Konfigurasi Streamlit Theme (`.streamlit/config.toml`)
Untuk menerapkan tema dasar AturModal secara otomatis ke komponen bawaan Streamlit, gunakan konfigurasi berikut:

```toml
[theme]
primaryColor = "#9d4300"
backgroundColor = "#fff8f5"
secondaryBackgroundColor = "#f6ece6"
textColor = "#1f1b17"
font = "sans-serif"
```

---

## 4. CSS Khusus untuk Streamlit UI (`styles.py`)
Karena Streamlit memiliki batasan styling bawaan, gaya visual Warm-Minimalist berikut harus diinjeksikan secara terprogram menggunakan `st.markdown` dengan `unsafe_allow_html=True`.

### Kode Custom CSS (Injeksi HTML):
```python
import streamlit as st

def apply_custom_design():
    custom_css = """
    <style>
        /* Impor Google Fonts */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
        
        /* Terapkan font ke seluruh aplikasi */
        html, body, [class*="css"], .stMarkdown, p, div, label {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
            color: #1f1b17;
        }

        /* Styling Sidebar (Left Panel) */
        [data-testid="stSidebar"] {
            background-color: #f6ece6 !important;
            border-right: 1px solid #e0c0b1;
        }

        /* Container Metrik Kustom (Card-style dengan border kiri) */
        .metric-card-primary {
            background-color: #ffffff;
            padding: 16px;
            border-radius: 12px;
            border-left: 4px solid #9d4300;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 12px;
        }
        .metric-card-secondary {
            background-color: #ffffff;
            padding: 16px;
            border-radius: 12px;
            border-left: 4px solid #006a61;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 12px;
        }
        .metric-card-tertiary {
            background-color: #ffffff;
            padding: 16px;
            border-radius: 12px;
            border-left: 4px solid #bfab56;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 12px;
        }
        .metric-title {
            font-size: 12px;
            font-weight: 600;
            color: #584237;
            margin-bottom: 4px;
        }
        .metric-value-primary {
            font-size: 24px;
            font-weight: 700;
            color: #9d4300;
        }
        .metric-value-secondary {
            font-size: 24px;
            font-weight: 700;
            color: #006a61;
        }
        .metric-value-tertiary {
            font-size: 24px;
            font-weight: 700;
            color: #6e5e0d;
        }

        /* Custom Scrollbar untuk Chat */
        ::-webkit-scrollbar {
            width: 6px;
        }
        ::-webkit-scrollbar-thumb {
            background-color: #e0c0b1;
            border-radius: 10px;
        }

        /* Status Pill */
        .status-pill {
            display: inline-flex;
            align-items: center;
            background-color: #ffdbca;
            color: #341100;
            padding: 6px 16px;
            border-radius: 9999px;
            font-weight: 600;
            font-size: 14px;
            gap: 8px;
            width: fit-content;
        }

        /* Desain Chat Bubble Kustom */
        /* Catatan: Streamlit memiliki st.chat_message bawaan. CSS ini menyelaraskan radius kelengkungannya. */
        [data-testid="stChatMessage"] {
            border-radius: 16px !important;
            border: 1px solid #e0c0b1 !important;
        }
        
        /* Menghapus garis pembagi bawaan Streamlit */
        hr {
            border-top: 1px solid #e0c0b1 !important;
        }
        
        /* Tombol Reset & Aksi */
        .stButton>button {
            border-radius: 12px !important;
            border: 2px solid #8c7164 !important;
            color: #584237 !important;
            background-color: transparent !important;
            font-weight: 600 !important;
            transition: all 0.2s ease-in-out;
        }
        .stButton>button:hover {
            background-color: #eae1da !important;
            color: #1f1b17 !important;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
```

---

## 5. Panduan Implementasi Layout & Komponen
1.  **Gunakan HTML Kustom untuk Metrik Sidebar:** 
    Jangan gunakan `st.metric` bawaan yang terlihat standar dan kaku. Gunakan kode HTML dengan kelas CSS yang telah ditentukan di atas agar terlihat seperti card premium dengan "Signature Stripe" (garis aksen kiri).
    *   *Contoh:*
        ```python
        st.sidebar.markdown(f'''
        <div class="metric-card-primary">
            <div class="metric-title">Total Belanja</div>
            <div class="metric-value-primary">Rp {st.session_state.total_belanja:,}</div>
        </div>
        ''', unsafe_allow_html=True)
        ```
2.  **Struktur Avatar Chat:**
    *   **User:** Gunakan emoji `👩‍🍳` atau `👤` (Align Right).
    *   **Assistant:** Gunakan emoji `🍳` (Align Left).
3.  **Ilustrasi State Kosong (Empty State):**
    Saat belum ada percakapan, tampilkan logo masakan hangat `🍳` atau gambar dapur minimalis, diikuti kutipan di tengah layar:
    > *"Keuntungan dimulai dari perhitungan yang tepat"*

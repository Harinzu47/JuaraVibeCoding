# FUNCTIONAL SPECIFICATION DOCUMENT (FSD)
**Project Name:** DapurProfit AI (Dynamic COGS & Revenue Tracker)
**Version:** 1.0
**Document Type:** Technical & Functional Blueprint

## 1. System Overview
DapurProfit AI adalah aplikasi web *single-page* berbasis *chat* yang mengandalkan LLM (Google Gemini API) sebagai pemroses logika utama (NLP *Engine*). Aplikasi ini tidak menggunakan basis data eksternal yang kompleks (seperti PostgreSQL/MySQL) untuk prototipe ini, melainkan memanfaatkan `st.session_state` di Streamlit untuk menyimpan memori komputasi finansial harian pengguna.

## 2. Tech Stack & Infrastructure
*   **Frontend & State Management:** Python (Streamlit Framework).
*   **NLP & Computation Engine:** Google Gemini API (menggunakan model `gemini-1.5-flash` atau `gemini-1.5-pro`).
*   **Deployment Environment:** Dockerized container, ditargetkan untuk *deploy* ke Google Cloud Run (Port 8080).

## 3. UI/UX & Layout Specification
Antarmuka dibangun menggunakan komponen standar Streamlit (`st.chat_message`, `st.chat_input`, `st.sidebar`) untuk memastikan responsivitas di perangkat seluler.

### 3.1. Main Layout
1.  **Header:** Judul aplikasi ("🍳 DapurProfit AI") dan subjudul singkat di area utama.
2.  **Sidebar (Panel Info Harian):**
    *   Menampilkan metrik state saat ini menggunakan `st.metric`.
    *   Indikator **"Modal Dikeluarkan Hari Ini"**: `Rp [total_belanja]` (Default: Rp 0).
    *   Indikator **"HPP per Porsi"**: `Rp [hpp_unit]` (Default: Rp 0).
    *   Indikator **"Fase Saat Ini"**: `[Pagi: Costing / Sore: Revenue]`.
    *   Tombol **"Reset Hari Ini"** (`st.button`) untuk menghapus session state dan memulai hari baru.
3.  **Main Chat Window:** Area utama yang merender iterasi dari `st.session_state.chat_history` (pesan *user* dan balasan *assistant*).
4.  **Chat Input Area:** Kolom teks interaktif di bagian bawah (`st.chat_input("Ketik belanjaan atau laporan jualan Ibu di sini...")`).

## 4. State Management (Session State Variables)
Streamlit wajib menginisialisasi variabel berikut di awal eksekusi skrip agar memori kalkulasi AI tidak terhapus saat interaksi (*rerun*):

- `st.session_state.chat_history` (List/Array): Menyimpan riwayat obrolan dalam format dictionary `{"role": "...", "content": "..."}`.
- `st.session_state.total_belanja` (Integer/Float): Total pengeluaran kasir (Default: 0).
- `st.session_state.modal_terpakai` (Integer/Float): Nilai uang dari bahan baku yang terpakai (Default: 0).
- `st.session_state.hpp_unit` (Integer/Float): Harga Pokok Penjualan per porsi masakan (Default: 0).
- `st.session_state.fase_saat_ini` (String): Menentukan konteks prompt AI. Nilai default: `"PAGI_COSTING"`. Berubah menjadi `"SORE_REVENUE"` setelah HPP terhitung.

## 5. Functional Workflows & System Interaction

### 5.1. Workflow 1: Initialization (App Load)
*   **Trigger:** Pengguna membuka aplikasi.
*   **Action:** Sistem memverifikasi ketersediaan `st.session_state`. Jika baru pertama kali dibuka (kosong), inisialisasi variabel dan render pesan pembuka.
*   **Output (System Message):** "Halo Ibu! 🍳 Hari ini mau masak apa? Yuk catat belanjaan dan jumlah porsi yang dibuat supaya kita bisa hitung modal dan harga jual yang pas!"

### 5.2. Workflow 2: Costing Phase (Fase Pagi)
*   **Trigger:** Pengguna menginput daftar belanja dan hasil masakan (kondisi state: `fase_saat_ini == "PAGI_COSTING"`).
*   **Backend Logic:**
    1. Input ditangkap oleh Streamlit.
    2. Streamlit merakit pesan berisi context instruksi perhitungan (lihat referensi prompt) + input user.
    3. Gemini API memproses dan mengembalikan respons berupa penjelasan teks natural dan blok JSON tersembunyi.
    4. Python *backend* mengekstrak JSON tersebut untuk meng-update variabel state (`total_belanja`, `modal_terpakai`, `hpp_unit`).
*   **Data Action:** Variabel state di-update. Sidebar otomatis ter-update pada *rerun* berikutnya.
*   **State Transition:** `st.session_state.fase_saat_ini` diubah menjadi `"SORE_REVENUE"`.

### 5.3. Workflow 3: Revenue Phase (Fase Sore)
*   **Trigger:** Pengguna melaporkan jumlah barang terjual (kondisi state: `fase_saat_ini == "SORE_REVENUE"`).
*   **Prasyarat/Validasi:** `st.session_state.hpp_unit` harus > 0.
*   **Backend Logic:**
    1. Input + nilai dari `session_state` disisipkan ke dalam prompt.
    2. Gemini mengkalkulasi Pemasukan, memotong Laba Bersih berdasarkan HPP, dan mengevaluasi status BEP (Break-Even Point).
*   **Output Action:** Render pesan hasil rekapitulasi laba rugi harian.

## 6. Error Handling & Edge Cases

| Skenario Kasus (Edge Case) | Respons Sistem (System Action) |
| :--- | :--- |
| **Input Kurang Lengkap** (Misal: Hanya menyebut nama makanan tanpa harga bahan) | AI tidak merender blok JSON, melainkan membalas dengan pertanyaan konfirmasi: "Wah kelihatannya enak! Tapi bahan-bahannya habis berapa rupiah Bu, dan jadi berapa porsi?" |
| **Lapor Jualan Tanpa HPP** (User melapor terjual, tapi belum input modal) | Python UI memblokir API call dengan Toast/Error atau AI merespons: "Alhamdulillah laku! Tapi kita belum hitung modalnya nih. Tadi pagi belanja habis berapa?" |
| **Satuan Tidak Terukur** (Misal: "garam secukupnya") | AI diprogram untuk mengabaikan biaya material "secukupnya" jika dianggap sepele (< Rp 1.000), atau menanyakan kembali untuk bahan utama. |
| **API Timeout / Error** | Tangkap `Exception` di blok `try-except`. Tampilkan `st.error("Maaf Bu, asisten sedang sibuk. Silakan coba kirim pesannya sekali lagi ya.")`. |

## 7. Integration with Google Gemini API (JSON Extraction Protocol)
Agar Streamlit dapat memperbarui Sidebar (State) dari *natural language response*, Gemini diinstruksikan menyisipkan data terstruktur dalam tag XML `<json_data>` di bagian paling bawah balasannya.

**Contoh Format Respons Gemini:**
```text
Wah, roti gorengnya pasti mantap Bu! Berikut rincian modalnya ya:
- Total Belanja: Rp 31.000
- Modal Kepake: Rp 14.000
- **HPP: Rp 700 / biji.**
Ibu bisa jual di harga Rp 2.000! 💰

<json_data>
{"total_spent": 31000, "used_cost": 14000, "hpp_unit": 700, "qty": 20}
</json_data>
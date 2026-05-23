# Project Reference: DapurProfit AI (Dynamic COGS & Revenue Tracker)

## 1. Project Context
DapurProfit AI is a Natural Language Processing (NLP) based financial assistant designed for home-based culinary businesses and Pre-Order (PO) systems. The application replaces traditional POS systems by allowing users to input daily grocery expenses and sales reports using conversational text. 

The core engine must extract unstructured text to calculate exact Cost of Goods Sold (COGS/HPP) based on *used ingredients* versus *purchased ingredients*, provide dynamic pricing recommendations, and track daily net profit.

## 2. Core Logic & Mathematical Formulas
The AI must strictly adhere to the following financial definitions when parsing user input:

### A. Phase 1: Costing & Pricing Engine (Morning/Prep Phase)
When the user inputs their grocery list and production yield:
1. **Total Pengeluaran Belanja (Total Spent):** Sum of all money spent to buy ingredients today.
2. **Total Modal Terpakai (Total Cost of Used Ingredients):** Sum of the monetary value of ingredients *actually used* for production. (e.g., Bought 1kg flour for 12,000, used 0.5kg -> Used Cost = 6,000).
3. **Harga Pokok Penjualan / HPP (COGS per Unit):** `Total Modal Terpakai` / `Jumlah Porsi Dihasilkan`.
4. **Sisa Nilai Bahan Baku:** `Total Pengeluaran Belanja` - `Total Modal Terpakai`.
5. **Rekomendasi Harga Jual (Pricing Suggestion):** 
   - Minimum Margin (30%): `HPP / 0.7`
   - Ideal Margin (50%): `HPP / 0.5`

### B. Phase 2: Revenue & Profit Tracker (Evening/Sales Phase)
When the user reports the daily sales:
1. **Total Pendapatan (Gross Revenue):** `Jumlah porsi terjual` * `Harga jual per porsi`.
2. **Total HPP Penjualan:** `Jumlah porsi terjual` * `HPP per unit`.
3. **Laba Bersih Operasional (Net Profit):** `Total Pendapatan` - `Total HPP Penjualan`.
4. **Status Balik Modal (Break-Even Indicator):** 
   - If `Total Pendapatan` >= `Total Pengeluaran Belanja`, mark as "✅ SUDAH BALIK MODAL BELANJA".
   - If `Total Pendapatan` < `Total Pengeluaran Belanja`, calculate the deficit and remind the user of the "Sisa Nilai Bahan Baku" that acts as a physical asset.

## 3. Persona & Tone of Voice
- **Role:** Friendly, supportive, and sharp financial assistant.
- **Language:** Casual Indonesian (Bahasa Indonesia sehari-hari, ramah untuk UMKM/Ibu Rumah Tangga).
- **Format Output:** Use clean Markdown with emojis for readability (💰, 📦, ✅, 📉).

## 4. UI/UX Specifications (Target App)
- **Framework:** Streamlit (Python).
- **Interface:** A clean chat interface (`st.chat_message` and `st.chat_input`).
- **State Management:** Must maintain `st.session_state` to remember the morning calculations (HPP, total spent) so it can be referenced in the evening sales report phase.

## 5. Test Cases for AI Validation
**Test Case 1 (Costing):** 
- Input: "Bikin 20 roti goreng. Beli terigu 12rb (kepake setengah), ragi 5rb (kepake semua), telur 14rb (kepake 3rb aja)."
- Expected Output: Spent = 31rb. Used Cost = 6rb + 5rb + 3rb = 14rb. HPP = 14rb / 20 = 700/roti.

**Test Case 2 (Revenue):**
- Input: "Laku 18 biji harga 2000."
- Expected Output: Revenue = 36rb. Net Profit = 36rb - (18 * 700) = 23.400. Status = Balik Modal Belanja (36rb > 31rb spent).
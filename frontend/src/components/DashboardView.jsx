import React, { useState } from 'react';
import { 
  TrendingUp, 
  Plus, 
  Download, 
  Trash2, 
  Calendar, 
  DollarSign, 
  Package, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  FileSpreadsheet
} from 'lucide-react';

export default function DashboardView({
  historyList = [],
  onDeleteHistoryItem,
  onClearHistory,
  onAddManualTransaction,
  onSaveTodaySession,
  todayData = {},
  faseSaatIni
}) {
  // Local state for Modals
  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [isSaveTodayModalOpen, setIsSaveTodayModalOpen] = useState(false);
  
  // Fields for manual entry
  const [manualName, setManualName] = useState('');
  const [manualDate, setManualDate] = useState(() => new Date().toISOString().split('T')[0]);
  const [manualTotalBelanja, setManualTotalBelanja] = useState('');
  const [manualModalTerpakai, setManualModalTerpakai] = useState('');
  const [manualHppUnit, setManualHppUnit] = useState('');
  const [manualPorsiTerjual, setManualPorsiTerjual] = useState('');
  const [manualHargaJual, setManualHargaJual] = useState('');

  // Field for naming today's session
  const [todaySessionName, setTodaySessionName] = useState('');

  // 1. CALCULATE KIP/KPI METRICS
  const totalRevenue = historyList.reduce((sum, item) => sum + (item.totalPendapatan || 0), 0);
  const totalProfit = historyList.reduce((sum, item) => sum + (item.labaBersih || 0), 0);
  const breakevenDaysCount = historyList.filter(item => item.isBreakeven).length;
  const bepRate = historyList.length > 0 ? Math.round((breakevenDaysCount / historyList.length) * 100) : 0;

  // 2. EXPORT CSV UTILITY
  const handleExportCSV = () => {
    if (historyList.length === 0) {
      alert("Belum ada data transaksi untuk diekspor, Bu!");
      return;
    }
    
    // CSV headers
    let csvContent = "data:text/csv;charset=utf-8,";
    csvContent += "ID,Tanggal,Nama Menu,Total Belanja,Modal Terpakai,HPP per Porsi,Porsi Terjual,Harga Jual,Total Pendapatan,Laba Bersih,Balik Modal\n";
    
    // CSV rows
    historyList.forEach(item => {
      const row = [
        item.id,
        `"${item.date}"`,
        `"${item.itemName}"`,
        item.totalBelanja,
        item.modalTerpakai,
        item.hppUnit,
        item.porsiTerjual,
        item.hargaJual,
        item.totalPendapatan,
        item.labaBersih,
        item.isBreakeven ? "YA" : "TIDAK"
      ].join(",");
      csvContent += row + "\n";
    });

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `DapurProfit_Laporan_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // 3. SUBMIT MANUAL TRANSACTION
  const handleManualSubmit = (e) => {
    e.preventDefault();
    if (!manualName.trim()) {
      alert("Nama Menu jualan tidak boleh kosong ya, Bu.");
      return;
    }

    const spent = parseInt(manualTotalBelanja) || 0;
    const used = parseInt(manualModalTerpakai) || 0;
    const hpp = parseInt(manualHppUnit) || 0;
    const sold = parseInt(manualPorsiTerjual) || 0;
    const price = parseInt(manualHargaJual) || 0;
    
    const revenue = sold * price;
    const profit = revenue - (sold * hpp);

    const newRecord = {
      id: Date.now().toString(),
      date: new Date(manualDate).toLocaleDateString('id-ID', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      }),
      itemName: manualName,
      totalBelanja: spent,
      modalTerpakai: used,
      hppUnit: hpp,
      porsiTerjual: sold,
      hargaJual: price,
      totalPendapatan: revenue,
      labaBersih: profit,
      isBreakeven: revenue >= spent
    };

    onAddManualTransaction(newRecord);
    
    // Clear and close
    setManualName('');
    setManualTotalBelanja('');
    setManualModalTerpakai('');
    setManualHppUnit('');
    setManualPorsiTerjual('');
    setManualHargaJual('');
    setIsManualModalOpen(false);
  };

  // 4. SUBMIT TODAY'S SESSION SAVE
  const handleSaveTodaySubmit = (e) => {
    e.preventDefault();
    const name = todaySessionName.trim() || "Dagangan Hari Ini";
    onSaveTodaySession(name);
    setTodaySessionName('');
    setIsSaveTodayModalOpen(false);
  };

  // Check if today has unsaved data (Total Belanja > 0)
  const hasUnsavedTodayData = todayData.totalBelanja > 0;

  // Format currency helpers
  const formatRp = (num) => {
    return "Rp " + (num || 0).toLocaleString('id-ID');
  };

  // Get last 7 days for the CSS chart
  const recentItems = [...historyList].slice(-7);
  const maxProfitForChart = Math.max(...recentItems.map(item => Math.abs(item.labaBersih || 0)), 10000);

  return (
    <div className="dashboard-container">
      {/* Header */}
      <header className="dashboard-header flex justify-between items-center">
        <div>
          <h1>📊 Riwayat Penjualan</h1>
          <p>Grafik performa bisnis kuliner Ibu berdasarkan catatan harian.</p>
        </div>
        <div className="flex gap-sm">
          <button className="btn btn-outline flex items-center gap-xs" onClick={handleExportCSV}>
            <Download size={16} />
            Unduh CSV (Excel)
          </button>
          <button className="btn btn-primary flex items-center gap-xs" onClick={() => setIsManualModalOpen(true)}>
            <Plus size={16} />
            Tambah Manual
          </button>
        </div>
      </header>

      {/* KPI Cards Grid */}
      <section className="dashboard-grid">
        <div className="kpi-card">
          <div className="kpi-icon profit"><TrendingUp size={24} /></div>
          <div className="kpi-details">
            <h3>Total Laba Bersih</h3>
            <p className="kpi-value text-teal">{formatRp(totalProfit)}</p>
            <span className="kpi-sub">Dari total jualan laku</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon revenue"><DollarSign size={24} /></div>
          <div className="kpi-details">
            <h3>Total Omzet</h3>
            <p className="kpi-value text-primary">{formatRp(totalRevenue)}</p>
            <span className="kpi-sub">Total seluruh pemasukan</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon bep"><CheckCircle size={24} /></div>
          <div className="kpi-details">
            <h3>Tingkat Balik Modal</h3>
            <p className="kpi-value text-amber">{bepRate}%</p>
            <span className="kpi-sub">{breakevenDaysCount} dari {historyList.length} hari balik modal</span>
          </div>
        </div>
        <div className="kpi-card">
          <div className="kpi-icon items"><Package size={24} /></div>
          <div className="kpi-details">
            <h3>Catatan Hari</h3>
            <p className="kpi-value">{historyList.length} Hari</p>
            <span className="kpi-sub">Total entri riwayat</span>
          </div>
        </div>
      </section>

      {/* Unsaved Session Alert Banner */}
      {hasUnsavedTodayData && (
        <div className="unsaved-banner flex justify-between items-center">
          <div className="flex items-center gap-sm">
            <AlertCircle size={24} className="text-primary" />
            <div>
              <h4>Ada transaksi obrolan hari ini yang belum disimpan!</h4>
              <p>Belanja: {formatRp(todayData.totalBelanja)} | HPP: {formatRp(todayData.hppUnit)} | Laba: {todayData.labaBersih !== null ? formatRp(todayData.labaBersih) : 'Belum input jualan sore'}</p>
            </div>
          </div>
          <button className="btn btn-primary btn-sm" onClick={() => setIsSaveTodayModalOpen(true)}>
            Simpan Laporan Hari Ini
          </button>
        </div>
      )}

      {/* Main Content Layout (Chart & Log Table) */}
      <div className="dashboard-content-split">
        {/* CSS Chart Section */}
        <div className="dashboard-card chart-section">
          <h3>📈 Tren Laba Harian (Maks. 7 Catatan Terakhir)</h3>
          {recentItems.length === 0 ? (
            <div className="empty-chart flex flex-col items-center justify-center">
              <p>Belum ada data untuk digambarkan. Yuk catat transaksi hari ini!</p>
            </div>
          ) : (
            <div className="chart-bar-container">
              {recentItems.map((item, index) => {
                const profit = item.labaBersih || 0;
                const isLoss = profit < 0;
                const heightPercentage = Math.min(Math.round((Math.abs(profit) / maxProfitForChart) * 100), 100) || 5;
                return (
                  <div key={item.id} className="chart-bar-wrapper">
                    <div className="chart-bar-value">{formatRp(profit)}</div>
                    <div className="chart-bar-track">
                      <div 
                        className={`chart-bar-fill ${isLoss ? 'loss' : 'gain'}`}
                        style={{ height: `${heightPercentage}%` }}
                        title={`${item.itemName}: Laba ${formatRp(profit)}`}
                      ></div>
                    </div>
                    <span className="chart-bar-label" title={item.itemName}>
                      {item.itemName.length > 10 ? item.itemName.substring(0, 8) + '..' : item.itemName}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* History List Section */}
        <div className="dashboard-card history-section">
          <div className="flex justify-between items-center margin-bottom-md">
            <h3>📋 Log Riwayat Transaksi</h3>
            {historyList.length > 0 && (
              <button className="btn-text text-red-600 flex items-center gap-xs" onClick={onClearHistory}>
                <Trash2 size={14} />
                Hapus Semua
              </button>
            )}
          </div>
          {historyList.length === 0 ? (
            <div className="empty-history flex flex-col items-center justify-center">
              <p>Belum ada riwayat transaksi yang tersimpan.</p>
            </div>
          ) : (
            <div className="history-table-wrapper">
              <table className="history-table">
                <thead>
                  <tr>
                    <th>Menu</th>
                    <th>Tanggal</th>
                    <th>Modal Belanja</th>
                    <th>Omzet</th>
                    <th>Laba Bersih</th>
                    <th>Status BEP</th>
                    <th>Aksi</th>
                  </tr>
                </thead>
                <tbody>
                  {[...historyList].reverse().map(item => (
                    <tr key={item.id}>
                      <td className="font-bold">{item.itemName}</td>
                      <td className="text-muted text-sm">{item.date.replace(/Hari|Senin|Selasa|Rabu|Kamis|Jumat|Sabtu|Minggu,?\s*/g, '')}</td>
                      <td>{formatRp(item.totalBelanja)}</td>
                      <td>{formatRp(item.totalPendapatan)}</td>
                      <td className={item.labaBersih >= 0 ? "text-teal font-bold" : "text-red-600 font-bold"}>
                        {formatRp(item.labaBersih)}
                      </td>
                      <td>
                        {item.isBreakeven ? (
                          <span className="badge badge-success flex items-center gap-xs">
                            <CheckCircle size={12} /> Balik Modal
                          </span>
                        ) : (
                          <span className="badge badge-warning flex items-center gap-xs">
                            <XCircle size={12} /> Belum BEP
                          </span>
                        )}
                      </td>
                      <td>
                        <button 
                          className="icon-btn text-muted hover-red"
                          onClick={() => onDeleteHistoryItem(item.id)}
                          title="Hapus Catatan"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* MODAL 1: TODAY SAVE NAMESPACE */}
      {isSaveTodayModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <header className="modal-header">
              <h3>🍳 Simpan Laporan Hari Ini</h3>
              <button className="close-btn" onClick={() => setIsSaveTodayModalOpen(false)}>&times;</button>
            </header>
            <form onSubmit={handleSaveTodaySubmit}>
              <div className="modal-body">
                <label>Nama Menu / Masakan Hari Ini</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={todaySessionName}
                  onChange={(e) => setTodaySessionName(e.target.value)}
                  placeholder="Misal: Roti Goreng Cokelat, Nasi Kuning"
                  required
                />
                <p className="helper-text">
                  Ini akan mengunci kalkulasi belanja pagi, harga pokok (HPP), dan penjualan sore hari ini ke dalam dashboard, lalu memulai sesi obrolan baru untuk besok pagi.
                </p>
              </div>
              <footer className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setIsSaveTodayModalOpen(false)}>Batal</button>
                <button type="submit" className="btn btn-primary">Simpan & Reset Obrolan</button>
              </footer>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: MANUAL TRANSACTION ADD */}
      {isManualModalOpen && (
        <div className="modal-backdrop">
          <div className="modal-card max-w-md">
            <header className="modal-header">
              <h3>📝 Tambah Transaksi Manual</h3>
              <button className="close-btn" onClick={() => setIsManualModalOpen(false)}>&times;</button>
            </header>
            <form onSubmit={handleManualSubmit}>
              <div className="modal-body grid-form">
                <div>
                  <label>Nama Menu Dagangan</label>
                  <input 
                    type="text" 
                    className="form-input" 
                    value={manualName} 
                    onChange={e => setManualName(e.target.value)} 
                    placeholder="Misal: Donat Kentang"
                    required 
                  />
                </div>
                <div>
                  <label>Tanggal Catatan</label>
                  <input 
                    type="date" 
                    className="form-input" 
                    value={manualDate} 
                    onChange={e => setManualDate(e.target.value)} 
                    required 
                  />
                </div>
                <div className="flex-row-form">
                  <div>
                    <label>Total Belanja (Rp)</label>
                    <input 
                      type="number" 
                      className="form-input" 
                      value={manualTotalBelanja} 
                      onChange={e => setManualTotalBelanja(e.target.value)} 
                      placeholder="60000"
                    />
                  </div>
                  <div>
                    <label>Modal Kepake (Rp)</label>
                    <input 
                      type="number" 
                      className="form-input" 
                      value={manualModalTerpakai} 
                      onChange={e => setManualModalTerpakai(e.target.value)} 
                      placeholder="40000"
                    />
                  </div>
                </div>
                <div className="flex-row-form">
                  <div>
                    <label>HPP per Porsi (Rp)</label>
                    <input 
                      type="number" 
                      className="form-input" 
                      value={manualHppUnit} 
                      onChange={e => setManualHppUnit(e.target.value)} 
                      placeholder="2000"
                    />
                  </div>
                </div>
                <div className="flex-row-form">
                  <div>
                    <label>Porsi Terjual</label>
                    <input 
                      type="number" 
                      className="form-input" 
                      value={manualPorsiTerjual} 
                      onChange={e => setManualPorsiTerjual(e.target.value)} 
                      placeholder="18"
                    />
                  </div>
                  <div>
                    <label>Harga Jual (Rp)</label>
                    <input 
                      type="number" 
                      className="form-input" 
                      value={manualHargaJual} 
                      onChange={e => setManualHargaJual(e.target.value)} 
                      placeholder="5000"
                    />
                  </div>
                </div>
                <p className="helper-text text-sm">
                  Omzet dan Laba Bersih akan dihitung secara otomatis berdasarkan porsi terjual, harga jual, dan HPP.
                </p>
              </div>
              <footer className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setIsManualModalOpen(false)}>Batal</button>
                <button type="submit" className="btn btn-primary">Tambahkan</button>
              </footer>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

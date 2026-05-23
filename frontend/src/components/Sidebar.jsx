import React from 'react';
import { 
  LayoutDashboard, 
  Settings, 
  RotateCcw, 
  Sun, 
  Sunset, 
  TrendingUp, 
  MessageSquare,
  Save
} from 'lucide-react';
import MetricCard from './MetricCard';

export default function Sidebar({
  totalBelanja,
  modalTerpakai,
  hppUnit,
  faseSaatIni,
  onChangeFase,
  onReset,
  activeTab,
  setActiveTab,
  onOpenSettings,
  isOpenMobile,
  toggleMobileSidebar,
  onOpenSaveTodayModal
}) {
  const formatRp = (val) => {
    return "Rp " + (val || 0).toLocaleString('id-ID');
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isOpenMobile && (
        <div className="sidebar-overlay" onClick={toggleMobileSidebar}></div>
      )}

      {/* Sidebar Aside Panel */}
      <aside className={`sidebar-panel ${isOpenMobile ? 'translate-x-0' : '-translate-x-full'}`}>
        {/* Sidebar Header */}
        <div className="sidebar-header">
          <div className="flex items-center gap-sm">
            <TrendingUp size={20} className="text-primary" />
            <h2>DapurProfit AI</h2>
          </div>
          <p>Pantauan modal & belanjaan terkini Ibu.</p>
        </div>

        {/* Metrics Cards Container */}
        <div className="metrics-container">
          <MetricCard title="Total Belanja" value={totalBelanja} type="primary" />
          <MetricCard title="Modal Kepake" value={modalTerpakai} type="secondary" />
          <MetricCard title="HPP per Porsi" value={hppUnit} type="tertiary" />

          <hr className="divider" />

          {/* Status Section (Segmented Control) */}
          <div className="status-section">
            <label className="section-label">Fase Transaksi Hari Ini</label>
            <div className="phase-toggle-container">
              <button 
                type="button"
                className={`phase-toggle-btn ${faseSaatIni === 'PAGI_COSTING' ? 'active' : ''}`}
                onClick={() => onChangeFase('PAGI_COSTING')}
              >
                <Sun size={14} />
                <span>🌅 Pagi</span>
              </button>
              <button 
                type="button"
                className={`phase-toggle-btn ${faseSaatIni === 'SORE_REVENUE' ? 'active' : ''}`}
                onClick={() => {
                  if (hppUnit <= 0) {
                    alert("Hitung modal belanja pagi dan HPP dulu ya Bu di obrolan!");
                    return;
                  }
                  onChangeFase('SORE_REVENUE');
                }}
              >
                <Sunset size={14} />
                <span>🌇 Sore</span>
              </button>
            </div>
          </div>

          <hr className="divider" />

          {/* Quick Actions */}
          <div className="flex flex-col gap-sm">
            {totalBelanja > 0 && (
              <button 
                className="btn btn-primary" 
                onClick={() => {
                  if (isOpenMobile) toggleMobileSidebar();
                  onOpenSaveTodayModal();
                }}
              >
                <Save size={16} />
                Simpan Transaksi
              </button>
            )}

            <button className="btn btn-outline" onClick={onReset}>
              <RotateCcw size={16} />
              Reset Hari Ini
            </button>
          </div>
        </div>

        {/* Sidebar Navigation */}
        <nav className="sidebar-nav">
          <div
            className={`nav-item ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('chat');
              if (isOpenMobile) toggleMobileSidebar();
            }}
          >
            <MessageSquare size={18} />
            Asisten Chat
          </div>
          <div
            className={`nav-item ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('dashboard');
              if (isOpenMobile) toggleMobileSidebar();
            }}
          >
            <LayoutDashboard size={18} />
            Riwayat Penjualan
          </div>
          <div
            className="nav-item"
            onClick={() => {
              onOpenSettings();
              if (isOpenMobile) toggleMobileSidebar();
            }}
          >
            <Settings size={18} />
            Pengaturan
          </div>
        </nav>
      </aside>
    </>
  );
}

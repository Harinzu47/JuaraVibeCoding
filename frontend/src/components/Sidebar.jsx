import React from 'react';
import { 
  LayoutDashboard, 
  Settings, 
  RotateCcw, 
  Sun, 
  Sunset, 
  TrendingUp, 
  MessageSquare,
  Save,
  LogOut
} from 'lucide-react';
import MetricCard from './MetricCard';

export default function Sidebar({
  totalSpending,
  usedCapital,
  cogsPerUnit,
  currentPhase,
  onChangePhase,
  onReset,
  activeTab,
  setActiveTab,
  onOpenSettings,
  isOpenMobile,
  toggleMobileSidebar,
  onOpenSaveTodayModal,
  currentUser,
  onLogout,
}) {
  // Generate initials from name or email
  const getInitials = () => {
    if (currentUser?.fullName) {
      return currentUser.fullName.trim().split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
    }
    if (currentUser?.email) return currentUser.email[0].toUpperCase();
    return '?';
  };

  return (
    <>
      {/* Mobile Overlay */}
      {isOpenMobile && (
        <div className="sidebar-overlay" onClick={toggleMobileSidebar}></div>
      )}

      {/* Sidebar Aside Panel */}
      <aside className={`sidebar-panel${isOpenMobile ? ' sidebar-open' : ''}`}>
        {/* Sidebar Header */}
        <div className="sidebar-header">
          <div className="flex items-center gap-sm">
            <TrendingUp size={20} className="text-primary" />
            <h2>AturModal</h2>
          </div>
          <p>Atur modal, raih untung maksimal.</p>
        </div>

        {/* Metrics Cards Container */}
        <div className="metrics-container">
          <MetricCard title="Total Belanja" value={totalSpending} type="primary" />
          <MetricCard title="Modal Kepake" value={usedCapital} type="secondary" />
          <MetricCard title="HPP per Porsi" value={cogsPerUnit} type="tertiary" />

          <hr className="divider" />

          {/* Status Section (Segmented Control) */}
          <div className="status-section">
            <label className="section-label">Fase Transaksi Hari Ini</label>
            <div className="phase-toggle-container">
              <button 
                type="button"
                className={`phase-toggle-btn ${currentPhase === 'MORNING_COSTING' ? 'active' : ''}`}
                onClick={() => onChangePhase('MORNING_COSTING')}
              >
                <Sun size={14} />
                <span>🌅 Pagi</span>
              </button>
              <button 
                type="button"
                className={`phase-toggle-btn ${currentPhase === 'EVENING_SALES' ? 'active' : ''}`}
                onClick={() => {
                  if (cogsPerUnit <= 0) {
                    alert("Hitung modal belanja pagi dan HPP dulu ya di obrolan!");
                    return;
                  }
                  onChangePhase('EVENING_SALES');
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
            {totalSpending > 0 && (
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

        {/* ── User Identity Card ── */}
        {currentUser && (
          <div className="user-card">
            <div className="user-card-avatar">{getInitials()}</div>
            <div className="user-card-info">
              <span className="user-card-name">
                {currentUser.fullName || 'Pengguna'}
              </span>
              <span className="user-card-email">{currentUser.email}</span>
            </div>
            <button
              className="user-card-logout"
              onClick={onLogout}
              title="Logout"
            >
              <LogOut size={15} />
            </button>
          </div>
        )}
      </aside>
    </>
  );
}



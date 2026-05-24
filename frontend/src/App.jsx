import React, { useState, useEffect } from 'react';
import { MessageSquare, LayoutDashboard, Settings as SettingsIcon } from 'lucide-react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import DashboardView from './components/DashboardView';
import SettingsModal from './components/SettingsModal';
import Login from './components/Login';

export default function App() {
  // =====================================================================
  // 1. STATE INITIALIZATION (Local Storage Persistent)
  // =====================================================================
  const [chatHistory, setChatHistory] = useState(() => {
    return JSON.parse(localStorage.getItem('dp_chat_history')) || [];
  });
  const [totalBelanja, setTotalBelanja] = useState(() => {
    return parseInt(localStorage.getItem('dp_total_belanja')) || 0;
  });
  const [modalTerpakai, setModalTerpakai] = useState(() => {
    return parseInt(localStorage.getItem('dp_modal_terpakai')) || 0;
  });
  const [hppUnit, setHppUnit] = useState(() => {
    return parseInt(localStorage.getItem('dp_hpp_unit')) || 0;
  });
  const [faseSaatIni, setFaseSaatIni] = useState(() => {
    return localStorage.getItem('dp_fase_saat_ini') || 'PAGI_COSTING';
  });
  const [healthStatus, setHealthStatus] = useState({
    gemini_configured: false,
    redis_connected: false
  });

  // State tambahan untuk jualan sore sebelum disimpan
  const [todayRevenue, setTodayRevenue] = useState(() => {
    return parseInt(localStorage.getItem('dp_today_revenue')) || 0;
  });
  const [todayProfit, setTodayProfit] = useState(() => {
    return parseInt(localStorage.getItem('dp_today_profit')) || 0;
  });
  const [todaySoldQty, setTodaySoldQty] = useState(() => {
    return parseInt(localStorage.getItem('dp_today_sold_qty')) || 0;
  });
  const [todayPricePerUnit, setTodayPricePerUnit] = useState(() => {
    return parseInt(localStorage.getItem('dp_today_price_per_unit')) || 0;
  });
  const [todayBreakeven, setTodayBreakeven] = useState(() => {
    return localStorage.getItem('dp_today_breakeven') === 'true';
  });

  // State Riwayat Penjualan (Dashboard)
  const [historyList, setHistoryList] = useState(() => {
    return JSON.parse(localStorage.getItem('dp_history')) || [];
  });

  // UI Toggles
  const [activeTab, setActiveTab] = useState('chat');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // State modal simpan hari ini (agar bisa dipicu dari sidebar)
  const [isSaveTodayOpen, setIsSaveTodayOpen] = useState(false);
  const [todaySessionName, setTodaySessionName] = useState('');

  // JWT Token State
  const [token, setToken] = useState(() => {
    return localStorage.getItem('dp_token') || '';
  });

  // =====================================================================
  // 2. STATE SAVE EFFECT
  // =====================================================================
  useEffect(() => {
    localStorage.setItem('dp_chat_history', JSON.stringify(chatHistory));
  }, [chatHistory]);

  useEffect(() => {
    localStorage.setItem('dp_total_belanja', totalBelanja.toString());
  }, [totalBelanja]);

  useEffect(() => {
    localStorage.setItem('dp_modal_terpakai', modalTerpakai.toString());
  }, [modalTerpakai]);

  useEffect(() => {
    localStorage.setItem('dp_hpp_unit', hppUnit.toString());
  }, [hppUnit]);

  useEffect(() => {
    localStorage.setItem('dp_fase_saat_ini', faseSaatIni);
  }, [faseSaatIni]);

  const fetchHealthStatus = async () => {
    try {
      const response = await fetch('/api/health');
      if (response.ok) {
        const data = await response.json();
        setHealthStatus({
          gemini_configured: data.gemini_configured,
          redis_connected: data.redis_connected
        });
      }
    } catch (err) {
      console.error("Gagal memuat status kesehatan API:", err);
    }
  };

  useEffect(() => {
    fetchHealthStatus();
  }, [isSettingsOpen]);

  useEffect(() => {
    localStorage.setItem('dp_today_revenue', todayRevenue.toString());
  }, [todayRevenue]);

  useEffect(() => {
    localStorage.setItem('dp_today_profit', todayProfit.toString());
  }, [todayProfit]);

  useEffect(() => {
    localStorage.setItem('dp_today_sold_qty', todaySoldQty.toString());
  }, [todaySoldQty]);

  useEffect(() => {
    localStorage.setItem('dp_today_price_per_unit', todayPricePerUnit.toString());
  }, [todayPricePerUnit]);

  useEffect(() => {
    localStorage.setItem('dp_today_breakeven', todayBreakeven.toString());
  }, [todayBreakeven]);

  useEffect(() => {
    localStorage.setItem('dp_history', JSON.stringify(historyList));
  }, [historyList]);

  useEffect(() => {
    if (token) {
      localStorage.setItem('dp_token', token);
    } else {
      localStorage.removeItem('dp_token');
    }
  }, [token]);

  // =====================================================================
  // 3. API CLIENT CALLS & ACTIONS
  // =====================================================================
  const handleSendMessage = async (messageText) => {
    const newUserMsg = { role: 'user', content: messageText };
    const updatedHistory = [...chatHistory, newUserMsg];
    setChatHistory(updatedHistory);
    setIsLoading(true);

    // Menggunakan Vite Proxy (/api/chat)
    const API_URL = '/api/chat';

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: messageText,
          chat_history: chatHistory,
          fase_saat_ini: faseSaatIni,
          total_belanja: totalBelanja,
          hpp_unit: hppUnit
        })
      });

      setIsLoading(false);

      if (!response.ok) {
        if (response.status === 401) {
          setToken(''); // Auto logout on invalid token
          throw new Error('Sesi kamu telah berakhir. Silakan login kembali.');
        }
        const errData = await response.json();
        throw new Error(errData.detail || 'Gagal terhubung dengan asisten.');
      }

      const data = await response.json();

      // Update metrik & fase dari balasan API
      setTotalBelanja(data.total_belanja);
      setModalTerpakai(data.modal_terpakai);
      setHppUnit(data.hpp_unit);
      setFaseSaatIni(data.fase_saat_ini);

      // Metrik sore (opsional)
      if (data.total_pendapatan !== null && data.total_pendapatan !== undefined) {
        setTodayRevenue(data.total_pendapatan);
      }
      if (data.laba_bersih !== null && data.laba_bersih !== undefined) {
        setTodayProfit(data.laba_bersih);
      }
      if (data.porsi_terjual !== null && data.porsi_terjual !== undefined) {
        setTodaySoldQty(data.porsi_terjual);
      }
      if (data.harga_jual !== null && data.harga_jual !== undefined) {
        setTodayPricePerUnit(data.harga_jual);
      }
      if (data.balik_modal !== null && data.balik_modal !== undefined) {
        setTodayBreakeven(data.balik_modal);
      }

      // Simpan balasan AI
      setChatHistory((prev) => [...prev, { role: 'assistant', content: data.response }]);

    } catch (err) {
      setIsLoading(false);
      setChatHistory((prev) => [
        ...prev,
        { role: 'assistant', content: err.message, isError: true }
      ]);
    }
  };

  // Reset Sesi Hari Ini
  const handleReset = () => {
    if (confirm('Apakah Ibu yakin ingin menghapus seluruh riwayat modal dan obrolan hari ini?')) {
      setChatHistory([]);
      setTotalBelanja(0);
      setModalTerpakai(0);
      setHppUnit(0);
      setFaseSaatIni('PAGI_COSTING');
      setTodayRevenue(0);
      setTodayProfit(0);
      setTodaySoldQty(0);
      setTodayPricePerUnit(0);
      setTodayBreakeven(false);
      
      // Bersihkan localStorage
      localStorage.removeItem('dp_chat_history');
      localStorage.removeItem('dp_total_belanja');
      localStorage.removeItem('dp_modal_terpakai');
      localStorage.removeItem('dp_hpp_unit');
      localStorage.removeItem('dp_fase_saat_ini');
      localStorage.removeItem('dp_today_revenue');
      localStorage.removeItem('dp_today_profit');
      localStorage.removeItem('dp_today_sold_qty');
      localStorage.removeItem('dp_today_price_per_unit');
      localStorage.removeItem('dp_today_breakeven');
    }
  };

  // Simpan Sesi Hari Ini ke Riwayat
  const handleSaveSession = (itemName) => {
    const finalRevenue = todayRevenue || (todaySoldQty * todayPricePerUnit);
    const finalProfit = todayProfit || (finalRevenue - (todaySoldQty * hppUnit));
    
    const newRecord = {
      id: Date.now().toString(),
      date: new Date().toLocaleDateString('id-ID', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      }),
      itemName: itemName || "Dagangan Hari Ini",
      totalBelanja: totalBelanja,
      modalTerpakai: modalTerpakai,
      hppUnit: hppUnit,
      porsiTerjual: todaySoldQty,
      hargaJual: todayPricePerUnit,
      totalPendapatan: finalRevenue,
      labaBersih: finalProfit,
      isBreakeven: todayBreakeven || (finalRevenue >= totalBelanja)
    };

    const updatedHistory = [...historyList, newRecord];
    setHistoryList(updatedHistory);

    // Reset today's stats
    setChatHistory([]);
    setTotalBelanja(0);
    setModalTerpakai(0);
    setHppUnit(0);
    setFaseSaatIni('PAGI_COSTING');
    setTodayRevenue(0);
    setTodayProfit(0);
    setTodaySoldQty(0);
    setTodayPricePerUnit(0);
    setTodayBreakeven(false);

    // Hapus obrolan dari storage
    localStorage.removeItem('dp_chat_history');
    localStorage.removeItem('dp_total_belanja');
    localStorage.removeItem('dp_modal_terpakai');
    localStorage.removeItem('dp_hpp_unit');
    localStorage.removeItem('dp_fase_saat_ini');
    localStorage.removeItem('dp_today_revenue');
    localStorage.removeItem('dp_today_profit');
    localStorage.removeItem('dp_today_sold_qty');
    localStorage.removeItem('dp_today_price_per_unit');
    localStorage.removeItem('dp_today_breakeven');

    alert("Laporan penjualan hari ini berhasil disimpan ke Riwayat!");
  };

  // Tambah Transaksi Manual
  const handleAddManualTransaction = (record) => {
    const updatedHistory = [...historyList, record];
    setHistoryList(updatedHistory);
  };

  // Hapus Satu Item Riwayat
  const handleDeleteHistoryItem = (id) => {
    if (confirm("Apakah Ibu yakin ingin menghapus catatan transaksi ini?")) {
      const updatedHistory = historyList.filter(item => item.id !== id);
      setHistoryList(updatedHistory);
    }
  };

  // Hapus Seluruh Riwayat
  const handleClearHistory = () => {
    if (confirm("Apakah Ibu yakin ingin menghapus seluruh riwayat penjualan? Tindakan ini tidak dapat dibatalkan!")) {
      setHistoryList([]);
      localStorage.removeItem('dp_history');
    }
  };



  const handleSaveTodaySubmit = (e) => {
    e.preventDefault();
    handleSaveSession(todaySessionName);
    setTodaySessionName('');
    setIsSaveTodayOpen(false);
  };

  if (!token) {
    return <Login setToken={setToken} />;
  }

  return (
    <div className="app-container">
      {/* Sidebar Component */}
      <Sidebar
        totalBelanja={totalBelanja}
        modalTerpakai={modalTerpakai}
        hppUnit={hppUnit}
        faseSaatIni={faseSaatIni}
        onChangeFase={setFaseSaatIni}
        onReset={handleReset}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenSettings={() => setIsSettingsOpen(true)}
        isOpenMobile={isMobileSidebarOpen}
        toggleMobileSidebar={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
        onOpenSaveTodayModal={() => setIsSaveTodayOpen(true)}
      />

      {/* Main Content Area: Chat or Dashboard */}
      {activeTab === 'chat' ? (
        <ChatArea
          chatHistory={chatHistory}
          faseSaatIni={faseSaatIni}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          toggleMobileSidebar={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
        />
      ) : (
        <DashboardView
          historyList={historyList}
          onDeleteHistoryItem={handleDeleteHistoryItem}
          onClearHistory={handleClearHistory}
          onAddManualTransaction={handleAddManualTransaction}
          onSaveTodaySession={handleSaveSession}
          todayData={{
            totalBelanja,
            modalTerpakai,
            hppUnit,
            totalPendapatan: todayRevenue,
            labaBersih: todayProfit,
            porsiTerjual: todaySoldQty,
            hargaJual: todayPricePerUnit,
            balikModal: todayBreakeven
          }}
          faseSaatIni={faseSaatIni}
        />
      )}

      {/* Mobile Bottom Navigation */}
      <nav className="mobile-navbar">
        <div
          className={`mobile-nav-item ${activeTab === 'chat' && !isSettingsOpen ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('chat');
            setIsSettingsOpen(false);
          }}
        >
          <MessageSquare size={20} />
          <span>Chat</span>
        </div>
        <div
          className={`mobile-nav-item ${activeTab === 'dashboard' && !isSettingsOpen ? 'active' : ''}`}
          onClick={() => {
            setActiveTab('dashboard');
            setIsSettingsOpen(false);
          }}
        >
          <LayoutDashboard size={20} />
          <span>Riwayat</span>
        </div>
        <div
          className={`mobile-nav-item ${isSettingsOpen ? 'active' : ''}`}
          onClick={() => {
            setIsSettingsOpen(true);
          }}
        >
          <SettingsIcon size={20} />
          <span>Pengaturan</span>
        </div>
      </nav>

      {/* Settings Modal Component */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        healthStatus={healthStatus}
        onLogout={() => setToken('')}
      />

      {/* Sidebar Quick-save Dialog Modal */}
      {isSaveTodayOpen && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <header className="modal-header">
              <h3>🍳 Simpan Transaksi Hari Ini</h3>
              <button className="close-btn" onClick={() => setIsSaveTodayOpen(false)}>&times;</button>
            </header>
            <form onSubmit={handleSaveTodaySubmit}>
              <div className="modal-body">
                <label>Nama Menu / Masakan Hari Ini</label>
                <input 
                  type="text" 
                  className="form-input" 
                  value={todaySessionName}
                  onChange={(e) => setTodaySessionName(e.target.value)}
                  placeholder="Misal: Nasi Uduk Komplit, Ayam Penyet"
                  required
                />
                <p className="helper-text">
                  Kalkulasi modal pagi, HPP, dan jualan sore akan diarsipkan ke dashboard, lalu sesi chat akan di-reset bersih untuk besok.
                </p>
              </div>
              <footer className="modal-footer">
                <button type="button" className="btn btn-outline" onClick={() => setIsSaveTodayOpen(false)}>Batal</button>
                <button type="submit" className="btn btn-primary">Simpan & Reset</button>
              </footer>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

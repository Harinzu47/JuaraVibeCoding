import React, { useState, useEffect } from 'react';
import { MessageSquare, LayoutDashboard, Settings as SettingsIcon } from 'lucide-react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import DashboardView from './components/DashboardView';
import SettingsModal from './components/SettingsModal';
import Login from './components/Login';
import Register from './components/Register';
import Toast from './components/Toast';

export default function App() {
  // =====================================================================
  // 0. ONE-TIME MIGRATION: Evict stale financial data from localStorage
  //    (These keys are no longer written — server is now Single Source of Truth)
  // =====================================================================
  (() => {
    const staleKeys = [
      'dp_chat_history', 'dp_total_spending', 'dp_used_capital',
      'dp_cogs_per_unit', 'dp_current_phase', 'dp_today_revenue',
      'dp_today_profit', 'dp_today_sold_qty', 'dp_today_price_per_unit',
      'dp_today_breakeven', 'dp_history'
    ];
    staleKeys.forEach(k => localStorage.removeItem(k));
  })();

  // =====================================================================
  // 1. STATE INITIALIZATION — always start clean, filled from server
  // =====================================================================

  const [chatHistory, setChatHistory] = useState([]);
  const [totalSpending, setTotalSpending] = useState(0);
  const [usedCapital, setUsedCapital] = useState(0);
  const [cogsPerUnit, setCogsPerUnit] = useState(0);
  const [currentPhase, setCurrentPhase] = useState('MORNING_COSTING');
  const [healthStatus, setHealthStatus] = useState({
    gemini_configured: false,
    redis_connected: false
  });

  // Additional states for evening sales
  const [todayRevenue, setTodayRevenue] = useState(0);
  const [todayProfit, setTodayProfit] = useState(0);
  const [todaySoldQty, setTodaySoldQty] = useState(0);
  const [todayPricePerUnit, setTodayPricePerUnit] = useState(0);
  const [todayBreakeven, setTodayBreakeven] = useState(false);

  // Saved History List state — always starts empty, filled from server
  const [historyList, setHistoryList] = useState([]);

  // UI Toggles
  const [activeTab, setActiveTab] = useState('chat');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // Quick save today states
  const [isSaveTodayOpen, setIsSaveTodayOpen] = useState(false);
  const [todaySessionName, setTodaySessionName] = useState('');

  // Daily Session ID
  const [currentSessionId, setCurrentSessionId] = useState(null);

  // JWT Token State
  const [token, setToken] = useState(() => {
    return localStorage.getItem('dp_token') || '';
  });

  // Current user info (from localStorage, set at login/register)
  const [currentUser, setCurrentUser] = useState(() => ({
    fullName: localStorage.getItem('dp_full_name') || '',
    email: localStorage.getItem('dp_email') || '',
  }));

  // Auth View State (login | register)
  const [authView, setAuthView] = useState('login');

  // Global Toast State
  const [globalToast, setGlobalToast] = useState(null);

  // =====================================================================
  // 2. STATE SAVE EFFECT
  // =====================================================================
  // Token is the ONLY thing persisted in localStorage
  useEffect(() => {
    if (token) {
      localStorage.setItem('dp_token', token);
    } else {
      localStorage.removeItem('dp_token');
    }
  }, [token]);

  const fetchHealthStatus = async () => {
    try {
      const response = await fetch('/api/health');
      if (response.ok) {
        const data = await response.json();
        setHealthStatus({
          gemini_configured: data.components.gemini.configured,
          redis_connected: data.components.redis.connected
        });
      }
    } catch (err) {
      console.error("Failed to load health status:", err);
    }
  };

  useEffect(() => {
    if (token) {
      fetchHealthStatus();
      fetchTodaySession();
      fetchHistoryList();
    }
  }, [isSettingsOpen, token]);

  const fetchTodaySession = async () => {
    try {
      const response = await fetch('/api/sessions/today', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setCurrentSessionId(data.id);
        
        // Always overwrite state from server (Single Source of Truth)
        setTotalSpending(data.total_spending || 0);
        setUsedCapital(data.used_capital || 0);
        setCogsPerUnit(data.cogs_per_unit || 0);
        setCurrentPhase(data.current_phase || 'MORNING_COSTING');
        setTodayRevenue(data.total_revenue || 0);
        setTodayProfit(data.net_profit || 0);
        setTodaySoldQty(data.portions_sold || 0);
        setTodayPricePerUnit(data.selling_price || 0);
        setTodayBreakeven(data.break_even || false);

        if (data.messages && data.messages.length > 0) {
          // Always set chat history from DB
          setChatHistory(data.messages.map(m => ({ role: m.role, content: m.content })));
        } else {
          // Fresh session — generate personalized greeting
          const userName = localStorage.getItem('dp_full_name');
          const sapaan = userName ? userName : "Kak/Ibu";
          setChatHistory([{ role: 'assistant', content: `Halo ${sapaan}! Yuk catat belanja modal dan pemasukan hari ini, biar AturModal yang hitung semuanya otomatis. Sudah belanja apa saja pagi ini ${sapaan}?` }]);
        }
      }
    } catch (err) {
      console.error("Failed to load today's session:", err);
    }
  };

  const fetchHistoryList = async () => {
    try {
      const response = await fetch('/api/sessions/', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        const todayStr = new Date().toISOString().split('T')[0]; // "YYYY-MM-DD"
        const mappedHistory = data
          .filter(session => session.session_date !== todayStr) // exclude today's active session
          .map(session => {
          const dateObj = new Date(session.session_date);
          return {
            id: session.id,
            date: dateObj.toLocaleDateString('id-ID', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }),
            rawDate: session.session_date,
            itemName: "Catatan Harian",
            totalSpending: session.total_spending,
            usedCapital: session.used_capital,
            cogsPerUnit: session.cogs_per_unit,
            portionsSold: session.portions_sold || 0,
            sellingPrice: session.selling_price || 0,
            totalRevenue: session.total_revenue || 0,
            netProfit: session.net_profit || 0,
            breakEven: session.break_even || false
          };
        });
        setHistoryList(mappedHistory);
      }
    } catch (err) {
      console.error("Failed to load history list:", err);
    }
  };



  // =====================================================================
  // 3. API CLIENT CALLS & ACTIONS
  // =====================================================================
  const handleSendMessage = async (messageText) => {
    const newUserMsg = { role: 'user', content: messageText };
    const updatedHistory = [...chatHistory, newUserMsg];
    setChatHistory(updatedHistory);
    setIsLoading(true);

    const API_URL = '/api/chat/';

    try {
      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: messageText,
          session_id: currentSessionId
        })
      });

      setIsLoading(false);

      if (!response.ok) {
        if (response.status === 401) {
          setToken(''); // Auto logout on token expiration
          throw new Error('Your session has expired. Please log in again.');
        }
        const errData = await response.json();
        throw new Error(errData.detail || 'Failed to connect with assistant.');
      }

      const data = await response.json();

      // Guard: only update if backend returns a meaningful value.
      if (data.total_spending !== null && data.total_spending !== undefined && data.total_spending > 0) {
        setTotalSpending(data.total_spending);
      }
      if (data.used_capital !== null && data.used_capital !== undefined && data.used_capital > 0) {
        setUsedCapital(data.used_capital);
      }
      if (data.cogs_per_unit !== null && data.cogs_per_unit !== undefined && data.cogs_per_unit > 0) {
        setCogsPerUnit(data.cogs_per_unit);
      }
      if (data.current_phase) {
        setCurrentPhase(data.current_phase);
      }

      // Optional evening metrics
      if (data.total_revenue !== null && data.total_revenue !== undefined) {
        setTodayRevenue(data.total_revenue);
      }
      if (data.net_profit !== null && data.net_profit !== undefined) {
        setTodayProfit(data.net_profit);
      }
      if (data.portions_sold !== null && data.portions_sold !== undefined) {
        setTodaySoldQty(data.portions_sold);
      }
      if (data.selling_price !== null && data.selling_price !== undefined) {
        setTodayPricePerUnit(data.selling_price);
      }
      if (data.break_even !== null && data.break_even !== undefined) {
        setTodayBreakeven(data.break_even);
      }

      // Save AI Chat response
      setChatHistory((prev) => [...prev, { role: 'assistant', content: data.response }]);

    } catch (err) {
      setIsLoading(false);
      setChatHistory((prev) => [
        ...prev,
        { role: 'assistant', content: err.message, isError: true }
      ]);
    }
  };

  const handleSendMessageStream = async (messageText) => {
    const newUserMsg = { role: 'user', content: messageText };
    setChatHistory(prev => [...prev, newUserMsg]);
    setIsLoading(true);

    const streamUrl = '/api/chat/stream';
    let assistantMsgIndex = -1;

    try {
      const response = await fetch(streamUrl, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: messageText,
          session_id: currentSessionId
        })
      });

      if (!response.ok) {
        if (response.status === 401) {
          setToken('');
          throw new Error('Your session has expired. Please log in again.');
        }
        throw new Error('Failed to connect with streaming assistant.');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let doneReading = false;
      let buffer = '';

      setChatHistory(prev => {
        assistantMsgIndex = prev.length;
        return [...prev, { role: 'assistant', content: 'Sedang berpikir...', isTyping: true }];
      });

      while (!doneReading) {
        const { value, done } = await reader.read();
        doneReading = done;
        if (value) {
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.replace('data: ', '').trim();
              if (!dataStr) continue;
              try {
                const event = JSON.parse(dataStr);
                
                if (event.type === 'thinking') {
                   // keep "Sedang berpikir..."
                } else if (event.type === 'done') {
                   const state = event.session_state;
                   if (state.total_spending > 0) setTotalSpending(state.total_spending);
                   if (state.used_capital > 0) setUsedCapital(state.used_capital);
                   if (state.cogs_per_unit > 0) setCogsPerUnit(state.cogs_per_unit);
                   if (state.current_phase) setCurrentPhase(state.current_phase);
                   
                   if (state.total_revenue !== null) setTodayRevenue(state.total_revenue);
                   if (state.net_profit !== null) setTodayProfit(state.net_profit);
                   if (state.portions_sold !== null) setTodaySoldQty(state.portions_sold);
                   if (state.selling_price !== null) setTodayPricePerUnit(state.selling_price);
                   if (state.break_even !== null) setTodayBreakeven(state.break_even);

                   setChatHistory(prev => {
                     const newHist = [...prev];
                     newHist[assistantMsgIndex] = { role: 'assistant', content: state.response, isTyping: false };
                     return newHist;
                   });
                } else if (event.type === 'error') {
                   throw new Error(event.content);
                }
              } catch (e) {
                console.error("SSE parse error", e, dataStr);
              }
            }
          }
        }
      }
      setIsLoading(false);
    } catch (err) {
      setIsLoading(false);
      setChatHistory(prev => {
        const newHist = [...prev];
        if (assistantMsgIndex !== -1) {
           newHist[assistantMsgIndex] = { role: 'assistant', content: err.message, isError: true, isTyping: false };
           return newHist;
        }
        return [...prev, { role: 'assistant', content: err.message, isError: true }];
      });
    }
  };

  // Reset Today's Session
  const handleReset = () => {
    if (confirm('Apakah Anda yakin ingin menghapus seluruh riwayat modal dan obrolan hari ini?')) {
      setChatHistory([]);
      setTotalSpending(0);
      setUsedCapital(0);
      setCogsPerUnit(0);
      setCurrentPhase('MORNING_COSTING');
      setTodayRevenue(0);
      setTodayProfit(0);
      setTodaySoldQty(0);
      setTodayPricePerUnit(0);
      setTodayBreakeven(false);
      // Also reset on server
      fetch('/api/sessions/today', {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      }).catch(err => console.error('Failed to reset session on server:', err));
    }
  };

  // Archive session to dashboard list
  const handleSaveSession = (itemName) => {
    const finalRevenue = todayRevenue || (todaySoldQty * todayPricePerUnit);
    const finalProfit = todayProfit || (finalRevenue - (todaySoldQty * cogsPerUnit));
    
    const newRecord = {
      id: Date.now().toString(),
      date: new Date().toLocaleDateString('id-ID', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      }),
      rawDate: new Date().toISOString().split('T')[0],
      itemName: itemName || "Dagangan Hari Ini",
      totalSpending: totalSpending,
      usedCapital: usedCapital,
      cogsPerUnit: cogsPerUnit,
      portionsSold: todaySoldQty,
      sellingPrice: todayPricePerUnit,
      totalRevenue: finalRevenue,
      netProfit: finalProfit,
      breakEven: todayBreakeven || (finalRevenue >= totalSpending)
    };

    const updatedHistory = [...historyList, newRecord];
    setHistoryList(updatedHistory);
    // Refresh from server to stay in sync
    fetchHistoryList();

    // Reset today's inputs
    setChatHistory([]);
    setTotalSpending(0);
    setUsedCapital(0);
    setCogsPerUnit(0);
    setCurrentPhase('MORNING_COSTING');
    setTodayRevenue(0);
    setTodayProfit(0);
    setTodaySoldQty(0);
    setTodayPricePerUnit(0);
    setTodayBreakeven(false);

    setGlobalToast("Laporan penjualan hari ini berhasil disimpan ke Riwayat!");
  };

  // Manual Transaction Add Handler
  const handleAddManualTransaction = (record) => {
    const updatedHistory = [...historyList, record];
    setHistoryList(updatedHistory);
  };

  // Update single history log
  const handleUpdateHistoryItem = (updatedRecord) => {
    const updatedHistory = historyList.map(item => 
      item.id === updatedRecord.id ? updatedRecord : item
    );
    setHistoryList(updatedHistory);
  };

  // Delete single history log
  const handleDeleteHistoryItem = (id) => {
    if (confirm("Apakah Ibu yakin ingin menghapus catatan transaksi ini?")) {
      const updatedHistory = historyList.filter(item => item.id !== id);
      setHistoryList(updatedHistory);
    }
  };

  // Clear all saved history logs
  const handleClearHistory = () => {
    if (confirm("Apakah Anda yakin ingin menghapus seluruh riwayat penjualan? Tindakan ini tidak dapat dibatalkan!")) {
      setHistoryList([]);
    }
  };

  const handleSaveTodaySubmit = (e) => {
    e.preventDefault();
    handleSaveSession(todaySessionName);
    setTodaySessionName('');
    setIsSaveTodayOpen(false);
  };

  // Secure Logout (Hard Reset)
  const handleLogout = () => {
    // Only 3 things are in localStorage now: token, full_name, email
    localStorage.removeItem('dp_token');
    localStorage.removeItem('dp_full_name');
    localStorage.removeItem('dp_email');
    
    // Hard navigate to trigger fresh React mount and dump all in-memory state
    window.location.href = '/';
  };

  if (!token) {
    return (
      <>
        <Toast message={globalToast} onClose={() => setGlobalToast(null)} />
        {authView === 'login' ? (
          <Login setToken={setToken} onToggleView={() => setAuthView('register')} />
        ) : (
          <Register setToken={setToken} onToggleView={() => setAuthView('login')} onSuccess={setGlobalToast} />
        )}
      </>
    );
  }

  return (
    <>
      <Toast message={globalToast} onClose={() => setGlobalToast(null)} />
      <div className="app-container">
      {/* Sidebar Component */}
      <Sidebar
        totalSpending={totalSpending}
        usedCapital={usedCapital}
        cogsPerUnit={cogsPerUnit}
        currentPhase={currentPhase}
        onChangePhase={setCurrentPhase}
        onReset={handleReset}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenSettings={() => setIsSettingsOpen(true)}
        isOpenMobile={isMobileSidebarOpen}
        toggleMobileSidebar={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
        onOpenSaveTodayModal={() => setIsSaveTodayOpen(true)}
        currentUser={currentUser}
        onLogout={handleLogout}
      />

      {/* Main Content Area */}
      {activeTab === 'chat' ? (
        <ChatArea
          chatHistory={chatHistory}
          currentPhase={currentPhase}
          onSendMessage={handleSendMessageStream}
          isLoading={isLoading}
          toggleMobileSidebar={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
        />
      ) : (
        <DashboardView
          historyList={historyList}
          onDeleteHistoryItem={handleDeleteHistoryItem}
          onClearHistory={handleClearHistory}
          onAddManualTransaction={handleAddManualTransaction}
          onUpdateHistoryItem={handleUpdateHistoryItem}
          onSaveTodaySession={handleSaveSession}
          todayData={{
            totalSpending,
            usedCapital,
            cogsPerUnit,
            totalRevenue: todayRevenue,
            netProfit: todayProfit,
            portionsSold: todaySoldQty,
            sellingPrice: todayPricePerUnit,
            breakEven: todayBreakeven
          }}
          currentPhase={currentPhase}
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
        onLogout={handleLogout}
      />

      {/* Quick Save Modal */}
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
    </>
  );
}

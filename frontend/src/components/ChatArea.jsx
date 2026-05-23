import React, { useState, useRef, useEffect } from 'react';
import { Menu, Send, AlertTriangle, Mic, MicOff } from 'lucide-react';

const parseMarkdown = (text) => {
  if (!text) return '';
  const lines = text.split('\n');
  const elements = [];
  let currentList = [];

  const parseInline = (lineText) => {
    const parts = [];
    let lastIndex = 0;
    const boldRegex = /\*\*(.*?)\*\*/g;
    let match;

    while ((match = boldRegex.exec(lineText)) !== null) {
      if (match.index > lastIndex) {
        parts.push(lineText.substring(lastIndex, match.index));
      }
      parts.push(<strong key={match.index}>{match[1]}</strong>);
      lastIndex = boldRegex.lastIndex;
    }

    if (lastIndex < lineText.length) {
      parts.push(lineText.substring(lastIndex));
    }

    return parts.length > 0 ? parts : lineText;
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();
    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const content = trimmed.substring(2);
      currentList.push(<li key={`li-${idx}`}>{parseInline(content)}</li>);
    } else {
      if (currentList.length > 0) {
        elements.push(<ul key={`ul-${idx}`} className="markdown-list">{currentList}</ul>);
        currentList = [];
      }
      if (trimmed === '') {
        elements.push(<div key={`br-${idx}`} className="markdown-space" />);
      } else {
        elements.push(<p key={`p-${idx}`} className="markdown-para">{parseInline(line)}</p>);
      }
    }
  });

  if (currentList.length > 0) {
    elements.push(<ul key={`ul-end`} className="markdown-list">{currentList}</ul>);
  }

  return elements;
};

export default function ChatArea({
  chatHistory,
  faseSaatIni,
  onSendMessage,
  isLoading,
  toggleMobileSidebar
}) {
  const [inputText, setInputText] = useState('');
  const chatBottomRef = useRef(null);

  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef(null);

  // Setup Web Speech API for Speech-to-Text
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const rec = new SpeechRecognition();
      rec.continuous = false;
      rec.interimResults = false;
      rec.lang = 'id-ID'; // Bahasa Indonesia

      rec.onstart = () => {
        setIsListening(true);
      };

      rec.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        setInputText((prev) => prev + (prev ? ' ' : '') + transcript);
      };

      rec.onerror = (e) => {
        console.error('Speech recognition error:', e);
        setIsListening(false);
      };

      rec.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = rec;
    }
  }, []);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert('Maaf Bu, browser ini tidak mendukung perekaman suara (Speech-to-Text). Silakan gunakan Google Chrome.');
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
    } else {
      try {
        recognitionRef.current.start();
      } catch (err) {
        console.error('Failed to start speech recognition:', err);
      }
    }
  };

  // Auto-scroll to bottom of chat when new messages arrive or loading state changes
  useEffect(() => {
    if (chatBottomRef.current) {
      chatBottomRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory, isLoading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmed = inputText.trim();
    if (trimmed && !isLoading) {
      onSendMessage(trimmed);
      setInputText('');
    }
  };

  const getPlaceholder = () => {
    return faseSaatIni === 'PAGI_COSTING'
      ? 'Ketik belanjaan atau modal pagi di sini...'
      : 'Lapor jualan sore di sini...';
  };

  const getExampleText = () => {
    return faseSaatIni === 'PAGI_COSTING'
      ? 'Contoh pagi: "Beli ayam 2kg 70rb, bawang merah 1/4kg 10rb. Jadi 20 porsi."'
      : 'Contoh sore: "Laku 18 porsi harga jual 10rb per porsi."';
  };

  return (
    <main className="chat-main">
      {/* Mobile header */}
      <header className="mobile-topbar">
        <span className="logo-text">DapurProfit AI</span>
        <button className="icon-btn text-primary" onClick={toggleMobileSidebar}>
          <Menu size={24} />
        </button>
      </header>

      {/* Chat Header (Desktop) */}
      <header className="chat-header">
        <h1 className="flex items-center gap-sm">
          <span className="logo-emoji">🍳</span>
          DapurProfit AI
        </h1>
        <p>Asisten Pintar Penghitung Modal & Laba Makanan</p>
      </header>

      {/* Chat Container */}
      <div className="chat-container">
        {chatHistory.length === 0 ? (
          <>
            <div className="chat-message-row assistant">
              <div className="chat-avatar">🍳</div>
              <div className="chat-bubble">
                Halo Ibu! 🍳 Hari ini mau masak apa? Yuk catat belanjaan dan jumlah porsi yang dibuat supaya kita bisa hitung modal dan harga jual yang pas!
              </div>
            </div>

            <div className="empty-state-container">
              <div className="empty-state-illustration">
                <img
                  src="https://lh3.googleusercontent.com/aida-public/AB6AXuB6tx7epXPsL8MzH2fw49CmBAV7_ebCp8WazQHZfErZAdig57MVzyWtOiiQMT-klroSDbNPwrlKgf27MLp_y4KNItLRVNj4rAEWVhNsU_PnpnN65tDocM9KpcMh5HRyUs-DJmmb65Pj3hnBYyK-_U3aC2zax-ViQZ-daLb7MaKUrO1ycDM7Shze_Py2gXZl_HvlRoV-_z3AJ5WRkokpcnbG7tWRCO9lFG8EPfgQ7etjF-R-U6ILsRqsHs30l1J4j4GwBoRaSup5U75A"
                  alt="Cooking tools scene"
                />
              </div>
              <p className="empty-state-quote">"Keuntungan dimulai dari perhitungan yang tepat"</p>
            </div>
          </>
        ) : (
          chatHistory.map((msg, index) => {
            const isUser = msg.role === 'user';
            const avatar = isUser ? '👩‍🍳' : '🍳';
            const isError = msg.isError;

            return (
              <div key={index} className={`chat-message-row ${isUser ? 'user' : 'assistant'}`}>
                <div className="chat-avatar">{isError ? <AlertTriangle size={18} className="text-red-600" /> : avatar}</div>
                <div
                  className="chat-bubble"
                  style={isError ? { borderColor: '#ba1a1a', backgroundColor: '#ffdad6', color: '#93000a' } : {}}
                >
                  {isError && <strong>Gagal memproses pesan: </strong>}
                  {isUser ? msg.content : parseMarkdown(msg.content)}
                </div>
              </div>
            );
          })
        )}

        {/* Skeleton Loader bubble */}
        {isLoading && (
          <div className="chat-message-row assistant">
            <div className="chat-avatar">🍳</div>
            <div className="chat-bubble skeleton-bubble"></div>
          </div>
        )}

        <div ref={chatBottomRef} />
      </div>

      {/* Bottom Chat Input */}
      <div className="chat-input-bar">
        <form className="input-form" onSubmit={handleSubmit}>
          <button
            type="button"
            className={`mic-btn ${isListening ? 'active' : ''}`}
            onClick={toggleListening}
            title={isListening ? 'Berhenti mendengarkan' : 'Bicara (Speech to Text)'}
            disabled={isLoading}
          >
            {isListening ? <MicOff size={20} /> : <Mic size={20} />}
          </button>
          <input
            className="input-field"
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={getPlaceholder()}
            disabled={isLoading}
            autoComplete="off"
          />
          <button className="send-btn" type="submit" disabled={isLoading || !inputText.trim()}>
            <Send size={18} />
          </button>
        </form>
        <p className="example-text">{getExampleText()}</p>
      </div>
    </main>
  );
}

import React, { useState, useEffect } from 'react';
import { Shield, CheckCircle } from 'lucide-react';

export default function SettingsModal({ isOpen, onClose, apiKey, onSave }) {
  const [keyInput, setKeyInput] = useState(apiKey);

  useEffect(() => {
    setKeyInput(apiKey);
  }, [apiKey, isOpen]);

  if (!isOpen) return null;

  const handleSave = () => {
    onSave(keyInput);
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="flex items-center gap-sm" style={{ fontWeight: 700 }}>
            <Shield size={18} className="text-primary" />
            Pengaturan Asisten
          </h3>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body">
          <label htmlFor="apiKeyInput" style={{ display: 'block', marginBottom: '4px', fontWeight: 600 }}>
            Google Gemini API Key:
          </label>
          <input
            type="password"
            id="apiKeyInput"
            value={keyInput}
            onChange={(e) => setKeyInput(e.target.value)}
            placeholder="Masukkan API Key Anda..."
            className="form-input"
          />
          <p className="helper-text" style={{ marginTop: '8px', fontSize: '12px', color: '#584237', opacity: 0.8 }}>
            Kunci API disimpan secara aman di browser lokal Anda (`localStorage`) dan hanya digunakan untuk mengirim permintaan ke Gemini API.
          </p>
        </div>
        <div className="modal-footer">
          <button className="btn btn-outline" onClick={onClose}>Batal</button>
          <button className="btn btn-primary flex items-center gap-sm" onClick={handleSave}>
            <CheckCircle size={16} />
            Simpan
          </button>
        </div>
      </div>
    </div>
  );
}

import React from 'react';
import { Shield, CheckCircle, AlertCircle } from 'lucide-react';

export default function SettingsModal({ isOpen, onClose, healthStatus = {}, onLogout }) {
  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3 className="flex items-center gap-sm" style={{ fontWeight: 700 }}>
            <Shield size={18} className="text-primary" />
            Status & Pengaturan Asisten
          </h3>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>
        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {/* Status Gemini */}
          <div className="status-item flex items-center justify-between" style={{ padding: '12px', backgroundColor: '#f6ece6', borderRadius: '8px' }}>
            <div>
              <strong style={{ display: 'block', fontSize: '14px' }}>Google Gemini AI</strong>
              <span className="text-muted text-sm" style={{ opacity: 0.8 }}>Model pemrosesan pintar asisten</span>
            </div>
            <div>
              {healthStatus.gemini_configured ? (
                <span className="badge badge-success flex items-center gap-xs">
                  <CheckCircle size={14} /> Terhubung
                </span>
              ) : (
                <span className="badge badge-warning flex items-center gap-xs" style={{ backgroundColor: '#ffdad6', color: '#ba1a1a' }}>
                  <AlertCircle size={14} /> Belum Config
                </span>
              )}
            </div>
          </div>

          {/* Status Redis */}
          <div className="status-item flex items-center justify-between" style={{ padding: '12px', backgroundColor: '#f6ece6', borderRadius: '8px' }}>
            <div>
              <strong style={{ display: 'block', fontSize: '14px' }}>Redis Rate Limiter</strong>
              <span className="text-muted text-sm" style={{ opacity: 0.8 }}>Sistem pembatas pesan (anti-spam)</span>
            </div>
            <div>
              {healthStatus.redis_connected ? (
                <span className="badge badge-success flex items-center gap-xs">
                  <CheckCircle size={14} /> Aktif (Redis)
                </span>
              ) : (
                <span className="badge badge-warning flex items-center gap-xs" style={{ backgroundColor: '#fef3c7', color: '#b45309' }}>
                  <AlertCircle size={14} /> Fail-Open (Off)
                </span>
              )}
            </div>
          </div>

          <p className="helper-text" style={{ fontSize: '12px', color: '#584237', opacity: 0.8, lineHeight: 1.4 }}>
            Demi alasan keamanan dan best practice industri, konfigurasi API key dan koneksi Redis sekarang diatur secara terpusat di sisi server (berkas `.env`).
          </p>
        </div>
        <div className="modal-footer" style={{ display: 'flex', justifyContent: 'space-between' }}>
          <button 
            className="btn btn-outline" 
            style={{ color: '#ba1a1a', borderColor: '#ba1a1a' }}
            onClick={() => {
              if (confirm('Apakah kamu yakin ingin logout?')) {
                onLogout();
              }
            }}
          >
            Logout
          </button>
          <button className="btn btn-primary" onClick={onClose}>Tutup</button>
        </div>
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import { ChefHat } from 'lucide-react';

export default function Register({ setToken, onToggleView }) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleRegister = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg('');

    if (password !== confirmPassword) {
      setErrorMsg('Password dan Konfirmasi Password tidak cocok');
      setIsLoading(false);
      return;
    }

    if (password.length < 8) {
      setErrorMsg('Password minimal 8 karakter');
      setIsLoading(false);
      return;
    }

    try {
      const response = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          email: email, 
          password: password,
          full_name: fullName || undefined
        })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Registrasi gagal');
      }

      // UX: Registrasi sukses, tampilkan alert lalu set token (Auto Login)
      alert('Registrasi Berhasil! Selamat datang di AturModal.');
      setToken(data.access_token);
      
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', backgroundColor: 'var(--bg-color)' }}>
      <div className="modal-card" style={{ maxWidth: '400px', width: '100%', padding: '2rem' }}>
        <header className="modal-header" style={{ justifyContent: 'center', borderBottom: 'none', flexDirection: 'column', gap: '1rem', paddingBottom: '0' }}>
          <div style={{ backgroundColor: 'var(--primary-color)', color: 'white', padding: '1rem', borderRadius: '50%' }}>
            <ChefHat size={40} />
          </div>
          <h2 style={{ textAlign: 'center', margin: 0 }}>Daftar AturModal</h2>
          <p style={{ textAlign: 'center', color: 'var(--text-light)', margin: 0 }}>Buat akun baru untuk mulai mengatur modal</p>
        </header>

        <form onSubmit={handleRegister} style={{ marginTop: '1.5rem' }}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {errorMsg && (
              <div style={{ padding: '0.75rem', backgroundColor: '#ffebee', color: '#c62828', borderRadius: '8px', fontSize: '14px', border: '1px solid #ffcdd2' }}>
                {errorMsg}
              </div>
            )}
            
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Nama Lengkap</label>
              <input 
                type="text" 
                className="form-input" 
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Nama Anda (Opsional)"
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Email</label>
              <input 
                type="email" 
                className="form-input" 
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="nama@email.com"
                required
              />
            </div>
            
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Password</label>
              <input 
                type="password" 
                className="form-input" 
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Minimal 8 karakter"
                required
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: '500' }}>Konfirmasi Password</label>
              <input 
                type="password" 
                className="form-input" 
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Ulangi password"
                required
              />
            </div>
          </div>
          
          <footer className="modal-footer" style={{ borderTop: 'none', paddingTop: '1.5rem', display: 'flex', flexDirection: 'column' }}>
            <button 
              type="submit" 
              className="btn btn-primary" 
              disabled={isLoading}
              style={{ width: '100%', justifyContent: 'center', padding: '0.75rem' }}
            >
              {isLoading ? 'Memproses...' : 'Daftar Sekarang'}
            </button>
            <p style={{ textAlign: 'center', fontSize: '14px', color: 'var(--text-light)', marginTop: '1rem' }}>
              Sudah punya akun?{' '}
              <span 
                style={{ color: 'var(--primary-color)', cursor: 'pointer', fontWeight: '500', textDecoration: 'underline' }}
                onClick={onToggleView}
              >
                Masuk di sini
              </span>
            </p>
          </footer>
        </form>
      </div>
    </div>
  );
}

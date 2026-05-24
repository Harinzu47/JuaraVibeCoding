import React, { useState } from 'react';
import { ChefHat } from 'lucide-react';

export default function Login({ setToken }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMsg('');

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Login gagal');
      }

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
          <h2 style={{ textAlign: 'center', margin: 0 }}>DapurProfit AI</h2>
          <p style={{ textAlign: 'center', color: 'var(--text-light)', margin: 0 }}>Login untuk melanjutkan sesi kamu</p>
        </header>

        <form onSubmit={handleLogin} style={{ marginTop: '1.5rem' }}>
          <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {errorMsg && (
              <div style={{ padding: '0.75rem', backgroundColor: '#ffebee', color: '#c62828', borderRadius: '8px', fontSize: '14px', border: '1px solid #ffcdd2' }}>
                {errorMsg}
              </div>
            )}
            
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
                placeholder="••••••••"
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
              {isLoading ? 'Memproses...' : 'Masuk'}
            </button>
            <p style={{ textAlign: 'center', fontSize: '13px', color: 'var(--text-light)', marginTop: '1rem' }}>
              Gunakan kredensial yang dibuat melalui Swagger/DB Seeder.
            </p>
          </footer>
        </form>
      </div>
    </div>
  );
}

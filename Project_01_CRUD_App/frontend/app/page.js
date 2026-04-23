"use client";
import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { fetchWithAuth } from '../lib/api';
import { useRouter } from 'next/navigation';

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const { login, token } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (token) router.push('/dashboard');
  }, [token, router]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      if (isLogin) {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const data = await fetchWithAuth('/token', {
          method: 'POST',
          body: formData,
        });
        login(data.access_token);
      } else {
        await fetchWithAuth('/register', {
          method: 'POST',
          body: JSON.stringify({ username, password }),
        });
        
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);
        const data = await fetchWithAuth('/token', {
          method: 'POST',
          body: formData,
        });
        login(data.access_token);
      }
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <main className="flex-center">
      <div className="glass-panel">
        <h2 style={{ marginBottom: '1.5rem', textAlign: 'center' }}>
          {isLogin ? 'Welcome Back' : 'Create Account'}
        </h2>
        {error && <div className="error-text">{error}</div>}
        <form onSubmit={handleSubmit}>
          <input
            type="text"
            className="input-field"
            placeholder="Username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
          <input
            type="password"
            className="input-field"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button type="submit" className="btn">
            {isLogin ? 'Log In' : 'Sign Up'}
          </button>
        </form>
        <p style={{ marginTop: '1.5rem', textAlign: 'center', fontSize: '0.9rem' }}>
          {isLogin ? "Don't have an account? " : "Already have an account? "}
          <span 
            style={{ color: 'var(--primary-color)', cursor: 'pointer', fontWeight: 'bold' }}
            onClick={() => setIsLogin(!isLogin)}
          >
            {isLogin ? 'Sign Up' : 'Log In'}
          </span>
        </p>
      </div>
    </main>
  );
}

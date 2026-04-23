"use client";
import './globals.css';
import { AuthProvider } from '../context/AuthContext';
import { useEffect, useState } from 'react';

export default function RootLayout({ children }) {
  const [theme, setTheme] = useState('dark');

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  return (
    <html lang="en" data-theme={theme}>
      <body>
        <AuthProvider>
          <div style={{ position: 'absolute', top: '1rem', right: '1rem' }}>
            <button className="theme-toggle" onClick={toggleTheme}>
              {theme === 'dark' ? '☀️ Light Mode' : '🌙 Dark Mode'}
            </button>
          </div>
          {children}
        </AuthProvider>
      </body>
    </html>
  );
}

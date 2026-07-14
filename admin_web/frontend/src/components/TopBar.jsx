import { useState, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';
import { User, LogOut, Sun, Moon } from 'lucide-react';

export default function TopBar({ title }) {
  const { user, logout } = useAuth();
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('theme') || 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === 'light' ? 'dark' : 'light'));
  };

  return (
    <header className="topbar">
      <div className="topbar-title">{title || 'SmartStudy Admin'}</div>
      <div className="topbar-right">
        <button
          className="btn btn-secondary btn-sm btn-icon"
          onClick={toggleTheme}
          title={`Switch to ${theme === 'light' ? 'Dark' : 'Light'} Mode`}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            borderRadius: '50%',
            padding: 0,
            width: '36px',
            height: '36px',
            border: '1px solid var(--border)',
          }}
        >
          {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
        </button>
        {user && (
          <div className="topbar-user">
            <div className="user-avatar">
              {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'A'}
            </div>
            <span className="topbar-user-name">{user.full_name}</span>
          </div>
        )}
        <button
          className="btn btn-secondary btn-sm"
          onClick={logout}
          title="Logout"
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <LogOut size={14} />
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
}

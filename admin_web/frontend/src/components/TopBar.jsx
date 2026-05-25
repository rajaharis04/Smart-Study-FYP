import { useAuth } from '../context/AuthContext';
import { User, LogOut } from 'lucide-react';

export default function TopBar({ title }) {
  const { user, logout } = useAuth();

  return (
    <header className="topbar">
      <div className="topbar-title">{title || 'SmartStudy Admin'}</div>
      <div className="topbar-right">
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

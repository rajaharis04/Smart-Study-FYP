import { useState } from 'react';
import { authApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Lock, Eye, EyeOff, CheckCircle, ShieldAlert } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function AccountsPage() {
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match.');
      return;
    }
    if (newPassword.length < 6) {
      toast.error('Password must be at least 6 characters.');
      return;
    }

    setLoading(true);
    try {
      await authApi.changePassword(currentPassword, newPassword);
      toast.success('Your administrator password has been updated!');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to change password.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '640px', margin: '0 auto' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Account Settings</h1>
          <p className="page-subtitle">Manage your administrator profile credentials and preferences.</p>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        {/* PROFILE OVERVIEW CARD */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="user-avatar" style={{ width: '40px', height: '40px', fontSize: '16px' }}>
              {user?.full_name?.charAt(0).toUpperCase() || 'A'}
            </div>
            <div>
              <h3 className="card-title">{user?.full_name}</h3>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>System Administrator</p>
            </div>
          </div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', borderBottom: '1px solid var(--border)', paddingBottom: '8px' }}>
              <span className="text-muted" style={{ fontSize: '13px' }}>Identity / Role</span>
              <span className="badge badge-accent" style={{ fontSize: '11px' }}>{user?.role}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', paddingBottom: '4px' }}>
              <span className="text-muted" style={{ fontSize: '13px' }}>Email Address</span>
              <span style={{ fontSize: '14px', fontWeight: 500 }}>{user?.email}</span>
            </div>
          </div>
        </div>

        {/* CHANGE PASSWORD CARD */}
        <div className="card">
          <div className="card-header">
            <h3 className="card-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Lock size={16} className="text-accent" />
              <span>Change Security Password</span>
            </h3>
          </div>
          <div className="card-body">
            <form onSubmit={handlePasswordChange} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {/* CURRENT */}
              <div className="form-group">
                <label className="form-label">Current Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showCurrent ? 'text' : 'password'}
                    className="form-control"
                    placeholder="Enter current password"
                    required
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setShowCurrent(!showCurrent)}
                    style={{
                      position: 'absolute',
                      right: '12px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      padding: '4px 8px',
                    }}
                  >
                    {showCurrent ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              {/* NEW */}
              <div className="form-group">
                <label className="form-label">New Password</label>
                <div style={{ position: 'relative' }}>
                  <input
                    type={showNew ? 'text' : 'password'}
                    className="form-control"
                    placeholder="At least 6 characters"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                  />
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => setShowNew(!showNew)}
                    style={{
                      position: 'absolute',
                      right: '12px',
                      top: '50%',
                      transform: 'translateY(-50%)',
                      padding: '4px 8px',
                    }}
                  >
                    {showNew ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              {/* CONFIRM NEW */}
              <div className="form-group">
                <label className="form-label">Confirm New Password</label>
                <input
                  type="password"
                  className="form-control"
                  placeholder="Repeat new password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>

              <button
                type="submit"
                className="btn btn-primary w-full"
                style={{ marginTop: '8px' }}
                disabled={loading}
              >
                {loading ? 'Updating Credentials...' : 'Change Password'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}

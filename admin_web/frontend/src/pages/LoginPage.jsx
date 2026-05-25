import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AlertCircle, ArrowLeft, CheckCircle2, ShieldCheck, Mail, Lock, KeyRound } from 'lucide-react';
import toast from 'react-hot-toast';

export default function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loginRole, setLoginRole] = useState('admin'); // 'admin' | 'teacher'
  const [isFirstTime, setIsFirstTime] = useState(false);
  const [firstTimeStep, setFirstTimeStep] = useState(0); // 0: Check Email, 1: Enter OTP, 2: Setup Password
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loadingStep, setLoadingStep] = useState(false);

  const { login, loading, verifyEmail, sendOtp, verifyOtp, setupPassword } = useAuth();
  const navigate = useNavigate();

  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    setError('');
    const res = await login(email, password);
    if (res.success) {
      // Validate that the returned user role matches what they selected (or automatically adjust)
      if (res.role !== loginRole) {
        toast.success(`Logged in successfully as ${res.role}!`);
      } else {
        toast.success('Logged in successfully!');
      }
      navigate('/');
    } else {
      setError(res.message);
    }
  };

  const handleFirstTimeSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoadingStep(true);

    try {
      if (firstTimeStep === 0) {
        // Step 0: Check email & Send OTP
        const verifyRes = await verifyEmail(email);
        if (!verifyRes.success) {
          setError(verifyRes.message);
          setLoadingStep(false);
          return;
        }

        const otpRes = await sendOtp(email);
        if (otpRes.success) {
          toast.success('OTP sent to your email address!');
          setFirstTimeStep(1);
        } else {
          setError(otpRes.message);
        }
      } else if (firstTimeStep === 1) {
        // Step 1: Verify OTP
        const otpVerifyRes = await verifyOtp(email, otp);
        if (otpVerifyRes.success) {
          toast.success('OTP verified successfully!');
          setFirstTimeStep(2);
        } else {
          setError(otpVerifyRes.message);
        }
      } else if (firstTimeStep === 2) {
        // Step 2: Setup password
        if (newPassword !== confirmPassword) {
          setError('Passwords do not match.');
          setLoadingStep(false);
          return;
        }
        if (newPassword.length < 6) {
          setError('Password must be at least 6 characters long.');
          setLoadingStep(false);
          return;
        }

        const setupRes = await setupPassword(email, otp, newPassword);
        if (setupRes.success) {
          toast.success('Password set successfully! You can now log in.');
          setIsFirstTime(false);
          setFirstTimeStep(0);
          setPassword('');
        } else {
          setError(setupRes.message);
        }
      }
    } catch (err) {
      setError('An unexpected error occurred. Please try again.');
    } finally {
      setLoadingStep(false);
    }
  };

  const handleResendOtp = async () => {
    setError('');
    toast.loading('Resending OTP...', { id: 'resend-otp' });
    const res = await sendOtp(email);
    if (res.success) {
      toast.success('A new OTP has been sent!', { id: 'resend-otp' });
    } else {
      toast.error(res.message, { id: 'resend-otp' });
      setError(res.message);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <div className="login-logo-icon">🎓</div>
          <div>
            <h1>SmartStudy</h1>
            <span>Portal Gateway</span>
          </div>
        </div>

        {/* Portal Options Tabs */}
        {!isFirstTime && (
          <div className="flex gap-2" style={{ marginBottom: '24px', background: 'var(--bg-input)', padding: '4px', borderRadius: 'var(--radius-sm)' }}>
            <button 
              type="button" 
              className={`btn w-full btn-sm`}
              onClick={() => { setLoginRole('admin'); setEmail(''); setPassword(''); setError(''); }}
              style={{ border: 'none', background: loginRole === 'admin' ? 'linear-gradient(135deg, var(--accent), var(--accent-dark))' : 'transparent', color: loginRole === 'admin' ? '#fff' : 'var(--text-secondary)', boxShadow: 'none', justifyContent: 'center' }}
            >
              Admin Portal
            </button>
            <button 
              type="button" 
              className={`btn w-full btn-sm`}
              onClick={() => { setLoginRole('teacher'); setEmail(''); setPassword(''); setError(''); }}
              style={{ border: 'none', background: loginRole === 'teacher' ? 'linear-gradient(135deg, var(--accent), var(--accent-dark))' : 'transparent', color: loginRole === 'teacher' ? '#fff' : 'var(--text-secondary)', boxShadow: 'none', justifyContent: 'center' }}
            >
              Teacher Portal
            </button>
          </div>
        )}

        {!isFirstTime ? (
          <>
            <h2 className="login-form-title">{loginRole === 'admin' ? 'Admin Sign In' : 'Teacher Sign In'}</h2>
            <p className="login-form-sub">Sign in to access your {loginRole === 'admin' ? 'administrator' : 'instructor'} dashboard.</p>

            {error && (
              <div className="login-error" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={18} />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleLoginSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="form-group">
                <label className="form-label" htmlFor="email">Email Address</label>
                <div style={{ position: 'relative' }}>
                  <Mail style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-secondary)' }} size={18} />
                  <input
                    id="email"
                    type="email"
                    className="form-control"
                    placeholder={loginRole === 'admin' ? 'admin@smartstudy.edu' : 'teacher@smartstudy.edu'}
                    required
                    style={{ paddingLeft: '38px' }}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>


              <div className="form-group">
                <label className="form-label" htmlFor="password">Password</label>
                <div style={{ position: 'relative' }}>
                  <Lock style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-secondary)' }} size={18} />
                  <input
                    id="password"
                    type="password"
                    className="form-control"
                    placeholder="••••••••"
                    required
                    style={{ paddingLeft: '38px' }}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </div>
              </div>

              <button
                type="submit"
                className="btn btn-primary w-full"
                style={{ marginTop: '8px' }}
                disabled={loading}
              >
                {loading ? 'Signing in...' : 'Sign In'}
              </button>
            </form>

            {loginRole === 'teacher' && (
              <div style={{ textAlign: 'center', marginTop: '20px' }}>
                <button 
                  type="button" 
                  className="btn btn-text"
                  onClick={() => {
                    setIsFirstTime(true);
                    setFirstTimeStep(0);
                    setError('');
                  }}
                  style={{ color: 'var(--accent)' }}
                >
                  First time logging in? Setup Password
                </button>
              </div>
            )}
          </>

        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
              <button
                type="button"
                className="btn-icon"
                onClick={() => {
                  if (firstTimeStep > 0) {
                    setFirstTimeStep(firstTimeStep - 1);
                  } else {
                    setIsFirstTime(false);
                  }
                  setError('');
                }}
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', color: 'var(--text-primary)' }}
              >
                <ArrowLeft size={20} />
              </button>
              <h2 className="login-form-title" style={{ margin: 0 }}>Initialize Account</h2>
            </div>
            <p className="login-form-sub">
              {firstTimeStep === 0 && "Enter your registered email to request an OTP."}
              {firstTimeStep === 1 && "Enter the 6-digit code sent to your email address."}
              {firstTimeStep === 2 && "Setup a secure password to finalize your account."}
            </p>

            {error && (
              <div className="login-error" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={18} />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleFirstTimeSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {firstTimeStep === 0 && (
                <div className="form-group">
                  <label className="form-label" htmlFor="email">Email Address</label>
                  <div style={{ position: 'relative' }}>
                    <Mail style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-secondary)' }} size={18} />
                    <input
                      id="email"
                      type="email"
                      className="form-control"
                      placeholder="name@smartstudy.edu"
                      required
                      style={{ paddingLeft: '38px' }}
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                    />
                  </div>
                </div>
              )}

              {firstTimeStep === 1 && (
                <div className="form-group">
                  <label className="form-label" htmlFor="otp">One-Time Password (OTP)</label>
                  <div style={{ position: 'relative' }}>
                    <KeyRound style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-secondary)' }} size={18} />
                    <input
                      id="otp"
                      type="text"
                      maxLength={6}
                      className="form-control"
                      placeholder="######"
                      required
                      style={{ paddingLeft: '38px', letterSpacing: '4px', textAlign: 'center', fontWeight: 'bold' }}
                      value={otp}
                      onChange={(e) => setOtp(e.target.value)}
                    />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
                    <button type="button" className="btn btn-text text-sm" onClick={handleResendOtp}>
                      Resend OTP Code
                    </button>
                  </div>
                </div>
              )}

              {firstTimeStep === 2 && (
                <>
                  <div className="form-group">
                    <label className="form-label" htmlFor="newPassword">New Password</label>
                    <div style={{ position: 'relative' }}>
                      <Lock style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-secondary)' }} size={18} />
                      <input
                        id="newPassword"
                        type="password"
                        className="form-control"
                        placeholder="Min 6 characters"
                        required
                        style={{ paddingLeft: '38px' }}
                        value={newPassword}
                        onChange={(e) => setNewPassword(e.target.value)}
                      />
                    </div>
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="confirmPassword">Confirm Password</label>
                    <div style={{ position: 'relative' }}>
                      <ShieldCheck style={{ position: 'absolute', left: '12px', top: '12px', color: 'var(--text-secondary)' }} size={18} />
                      <input
                        id="confirmPassword"
                        type="password"
                        className="form-control"
                        placeholder="Re-enter password"
                        required
                        style={{ paddingLeft: '38px' }}
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                      />
                    </div>
                  </div>
                </>
              )}

              <button
                type="submit"
                className="btn btn-primary w-full"
                style={{ marginTop: '8px' }}
                disabled={loadingStep}
              >
                {loadingStep ? 'Processing...' : (
                  firstTimeStep === 0 ? 'Send OTP' : (firstTimeStep === 1 ? 'Verify OTP' : 'Finalize Password')
                )}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}

import { createContext, useContext, useState, useEffect } from 'react';
import { authApi } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    const stored = localStorage.getItem('admin_user');
    return stored ? JSON.parse(stored) : null;
  });
  const [loading, setLoading] = useState(false);

  const login = async (email, password) => {
    setLoading(true);
    try {
      const res = await authApi.login(email, password);
      const { access_token, full_name, role } = res.data;
      localStorage.setItem('admin_token', access_token);
      const userData = { full_name, role, email };
      localStorage.setItem('admin_user', JSON.stringify(userData));
      setUser(userData);
      return { success: true };
    } catch (err) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Login failed.',
      };
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    setUser(null);
  };

  const verifyEmail = async (email) => {
    try {
      const res = await authApi.verifyEmail(email);
      return { success: true, data: res.data };
    } catch (err) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Email verification failed.',
      };
    }
  };

  const sendOtp = async (email) => {
    try {
      const res = await authApi.sendOtp(email);
      return { success: true, message: res.data.message };
    } catch (err) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Failed to send OTP.',
      };
    }
  };

  const verifyOtp = async (email, otp) => {
    try {
      const res = await authApi.verifyOtp(email, otp);
      return { success: true, message: res.data.message };
    } catch (err) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Invalid or expired OTP.',
      };
    }
  };

  const setupPassword = async (email, otp, password) => {
    try {
      const res = await authApi.setupPassword(email, otp, password);
      return { success: true, message: res.data.message };
    } catch (err) {
      return {
        success: false,
        message: err.response?.data?.detail || 'Failed to set up password.',
      };
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        login,
        logout,
        loading,
        verifyEmail,
        sendOtp,
        verifyOtp,
        setupPassword,
      }}
    >
      {children}
    </AuthContext.Provider>
  );

}

export function useAuth() {
  return useContext(AuthContext);
}

export function RequireAuth({ children }) {
  const { user } = useAuth();
  if (!user) {
    window.location.href = '/login';
    return null;
  }
  return children;
}

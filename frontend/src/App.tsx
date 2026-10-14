import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';

// Layouts
import { AppLayout } from './layouts/AppLayout';

// Auth Pages
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ForgotPassword } from './pages/ForgotPassword';
import { ResetPassword } from './pages/ResetPassword';

// Main Application Pages
import { Dashboard } from './pages/Dashboard';
import { Investigate } from './pages/Investigate';
import { TrustedIdentity } from './pages/TrustedIdentity';
import { ScamDna } from './pages/ScamDna';
import { ThreatGraph } from './pages/ThreatGraph';
import { AppAnalysis } from './pages/AppAnalysis';
import { ThreatIntelligence } from './pages/ThreatIntelligence';
import { CriticalAlerts } from './pages/CriticalAlerts';
import { CaseHistory } from './pages/CaseHistory';
import { Reports } from './pages/Reports';
import { SafetyCopilot } from './pages/SafetyCopilot';
import { SettingsPage } from './pages/Settings';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F1F7FF]">
        <div className="w-10 h-10 border-4 border-[#087CF0] border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public Auth Routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />

          {/* Main App Routes with Shared Sidebar & Topbar Layout */}
          <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/investigate" element={<Investigate />} />
            <Route path="/trusted-identity" element={<TrustedIdentity />} />
            <Route path="/scam-dna" element={<ScamDna />} />
            <Route path="/threat-graph" element={<ThreatGraph />} />
            <Route path="/app-analysis" element={<AppAnalysis />} />
            <Route path="/threat-intelligence" element={<ThreatIntelligence />} />
            <Route path="/critical-alerts" element={<CriticalAlerts />} />
            <Route path="/case-history" element={<CaseHistory />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/safety-copilot" element={<SafetyCopilot />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Route>

          {/* Fallback & Root */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
};

export default App;

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Mail, Lock, Eye, EyeOff, Search, Brain,
  UserCheck, Users, GraduationCap, Building2,
  Landmark, ShieldCheck, Heart, Globe, ArrowRight
} from 'lucide-react';
import { BrandLogo } from '../components/BrandLogo';
import { ShieldGraphic } from '../components/ShieldGraphic';
import { RudraMascot } from '../components/RudraMascot';
import { useAuth } from '../context/AuthContext';

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [language, setLanguage] = useState<'en' | 'te'>('en');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!usernameOrEmail || !password) {
      setErrorMessage('Please enter your email/username and password.');
      return;
    }
    setLoading(true);
    setErrorMessage('');
    try {
      await login({ username_or_email: usernameOrEmail, password });
      navigate('/dashboard');
    } catch (err: any) {
      setErrorMessage(err.response?.data?.detail || 'Invalid email or password. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-[#E6F2FF] via-[#F1F7FF] to-[#DDF1FF] flex items-center justify-center p-4 sm:p-6 lg:p-8 font-sans">
      <div className="w-full max-w-7xl grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">

        {/* ================= LEFT HERO COLUMN (REFERENCE B) ================= */}
        <div className="lg:col-span-7 flex flex-col justify-between py-4 lg:py-6 px-2 sm:px-6">
          {/* Logo Header */}
          <div className="mb-6">
            <BrandLogo size="md" variant="light" />
          </div>

          {/* Hero Headline */}
          <div className="space-y-3 mb-6">
            <h1 className="text-3xl sm:text-4xl lg:text-[42px] font-extrabold text-[#061A3A] tracking-tight leading-[1.15]">
              Smarter Protection <br />
              for a <span className="text-[#087CF0]">Safer Digital World</span>
            </h1>
            <p className="text-sm sm:text-base text-[#657792] max-w-xl font-normal leading-relaxed">
              RudraShield AI applies explainable detection, identity checks, and threat triage to spot scam signals and suspicious indicators before they spread.
            </p>
          </div>

          {/* 4 Feature Pills Matching Reference B */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 my-2">
            {/* Pill 1: Detect Scams */}
            <div className="flex items-center gap-2.5 bg-white/90 backdrop-blur-sm px-3.5 py-2 rounded-full border border-[#DCE7F5] shadow-sm">
              <div className="w-7 h-7 rounded-full bg-[#087CF0] flex items-center justify-center text-white flex-shrink-0">
                <Search className="w-3.5 h-3.5" />
              </div>
              <span className="text-xs font-semibold text-[#102447]">Detect Scams</span>
            </div>

            {/* Pill 2: Analyze Threats */}
            <div className="flex items-center gap-2.5 bg-white/90 backdrop-blur-sm px-3.5 py-2 rounded-full border border-[#DCE7F5] shadow-sm">
              <div className="w-7 h-7 rounded-full bg-[#8B5CF6] flex items-center justify-center text-white flex-shrink-0">
                <Brain className="w-3.5 h-3.5" />
              </div>
              <span className="text-xs font-semibold text-[#102447]">Analyze Threats</span>
            </div>

            {/* Pill 3: Verify Identities */}
            <div className="flex items-center gap-2.5 bg-white/90 backdrop-blur-sm px-3.5 py-2 rounded-full border border-[#DCE7F5] shadow-sm">
              <div className="w-7 h-7 rounded-full bg-[#12B981] flex items-center justify-center text-white flex-shrink-0">
                <UserCheck className="w-3.5 h-3.5" />
              </div>
              <span className="text-xs font-semibold text-[#102447]">Verify Identities</span>
            </div>

            {/* Pill 4: Protect Everyone */}
            <div className="flex items-center gap-2.5 bg-white/90 backdrop-blur-sm px-3.5 py-2 rounded-full border border-[#DCE7F5] shadow-sm">
              <div className="w-7 h-7 rounded-full bg-[#F59E0B] flex items-center justify-center text-white flex-shrink-0">
                <Users className="w-3.5 h-3.5" />
              </div>
              <span className="text-xs font-semibold text-[#102447]">Protect Everyone</span>
            </div>
          </div>

          {/* Central 3D Cyber Shield Illustration */}
          <div className="flex justify-center my-2">
            <ShieldGraphic />
          </div>

          {/* Trusted by Footer */}
          <div className="pt-2 border-t border-[#DCE7F5]/70">
            <p className="text-[11px] font-semibold text-[#657792] mb-3 uppercase tracking-wider text-center sm:text-left">
              Trusted by
            </p>
            <div className="flex flex-wrap items-center justify-center sm:justify-start gap-6 text-[#102447]">
              <div className="flex items-center gap-1.5 text-xs font-medium">
                <GraduationCap className="w-4 h-4 text-[#087CF0]" />
                <span>Students</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-medium">
                <Users className="w-4 h-4 text-[#087CF0]" />
                <span>Families</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-medium">
                <Building2 className="w-4 h-4 text-[#087CF0]" />
                <span>Businesses</span>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-medium">
                <Landmark className="w-4 h-4 text-[#087CF0]" />
                <span>Government</span>
              </div>
            </div>
          </div>
        </div>

        {/* ================= RIGHT LOGIN CARD (REFERENCE B) ================= */}
        <div className="lg:col-span-5 flex justify-center">
          <div className="w-full max-w-md bg-white rounded-[28px] shadow-[0_12px_40px_rgba(6,26,58,0.08)] border border-[#DCE7F5] p-7 sm:p-9 relative">

            {/* Language Selector Top Right */}
            <div className="flex justify-end mb-2">
              <div className="relative inline-flex items-center text-xs font-medium text-[#657792] hover:text-[#087CF0] cursor-pointer">
                <Globe className="w-3.5 h-3.5 mr-1" />
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value as 'en' | 'te')}
                  className="bg-transparent border-none py-1 pl-1 pr-4 text-xs font-medium text-[#102447] focus:outline-none cursor-pointer"
                >
                  <option value="en">English ▾</option>
                  <option value="te">తెలుగు ▾</option>
                </select>
              </div>
            </div>

            {/* Header */}
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-[#102447] flex items-center gap-2">
                Welcome Back! <span className="text-2xl">👋</span>
              </h2>
              <p className="text-xs text-[#657792] mt-1 font-medium">
                Sign in to continue to your RudraShield AI account
              </p>
            </div>

            {/* Error Message */}
            {errorMessage && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-xl text-xs flex items-center">
                <span>{errorMessage}</span>
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email / Username */}
              <div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#8E9EB5]">
                    <Mail className="w-4 h-4" />
                  </div>
                  <input
                    type="text"
                    value={usernameOrEmail}
                    onChange={(e) => setUsernameOrEmail(e.target.value)}
                    placeholder="Email or Username"
                    className="w-full pl-10 pr-4 py-3 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-sm text-[#102447] placeholder-[#8E9EB5] focus:outline-none focus:border-[#087CF0] focus:ring-2 focus:ring-[#087CF0]/20 transition-all"
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-[#8E9EB5]">
                    <Lock className="w-4 h-4" />
                  </div>
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Password"
                    className="w-full pl-10 pr-10 py-3 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-sm text-[#102447] placeholder-[#8E9EB5] focus:outline-none focus:border-[#087CF0] focus:ring-2 focus:ring-[#087CF0]/20 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-3.5 flex items-center text-[#8E9EB5] hover:text-[#087CF0]"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Forgot Password Link */}
              <div className="flex justify-end">
                <Link
                  to="/forgot-password"
                  className="text-xs font-semibold text-[#087CF0] hover:underline"
                >
                  Forgot Password?
                </Link>
              </div>

              {/* Primary Login Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 bg-gradient-to-r from-[#087CF0] to-[#06C8F9] hover:from-[#076ecc] hover:to-[#05b8e5] text-white font-semibold rounded-xl text-sm shadow-md shadow-blue-500/25 flex items-center justify-center gap-2 transition-all transform active:scale-[0.98] disabled:opacity-70"
              >
                {loading ? (
                  <span>Authenticating...</span>
                ) : (
                  <>
                    <ArrowRight className="w-4 h-4" />
                    <span>Login</span>
                  </>
                )}
              </button>

            </form>

            {/* OR Divider */}
            <div className="relative my-4 flex items-center justify-center">
              <div className="border-t border-[#E2E8F0] w-full" />
              <span className="bg-white px-3 text-[11px] font-bold text-[#8E9EB5] absolute">OR</span>
            </div>

            {/* OAuth Buttons */}
            <div className="space-y-2">
              <button
                type="button"
                onClick={() => alert("Google sign-in is not configured in this build.")}
                className="w-full py-2.5 px-4 bg-white hover:bg-gray-50 border border-[#DCE7F5] rounded-xl text-xs font-semibold text-[#102447] flex items-center justify-center gap-2.5 transition-colors shadow-sm"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                Continue with Google
              </button>

              <button
                type="button"
                onClick={() => alert("GitHub sign-in is not configured in this build.")}
                className="w-full py-2.5 px-4 bg-white hover:bg-gray-50 border border-[#DCE7F5] rounded-xl text-xs font-semibold text-[#102447] flex items-center justify-center gap-2.5 transition-colors shadow-sm"
              >
                <svg className="w-4 h-4 fill-current text-[#102447]" viewBox="0 0 24 24">
                  <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
                </svg>
                Continue with GitHub
              </button>
            </div>

            {/* Sign Up Link */}
            <div className="mt-4 text-center">
              <span className="text-xs text-[#657792]">Don't have an account? </span>
              <Link to="/register" className="text-xs font-bold text-[#087CF0] hover:underline">
                Sign Up ➔
              </Link>
            </div>

            {/* AI Assistant Teaser Card Matching Reference B */}
            <div className="mt-5 p-3.5 bg-gradient-to-r from-[#EBF5FF] to-[#F1F9FF] border border-[#CFE5FF] rounded-2xl flex items-center justify-between gap-3 shadow-inner">
              <div className="flex items-center gap-3">
                <RudraMascot className="w-10 h-10" />
                <p className="text-[11px] text-[#102447] leading-tight">
                  <span className="font-semibold text-[#087CF0]">Hi! I'm Rudra</span>, your AI security assistant. Ask me anything about scams, links, profiles or upload a screenshot.
                </p>
              </div>
              <Link
                to="/safety-copilot"
                className="px-2.5 py-1.5 bg-[#087CF0] hover:bg-[#076ecc] text-white text-[11px] font-semibold rounded-lg whitespace-nowrap transition-colors flex items-center gap-1 shadow-sm"
              >
                <span>Try Now</span>
                <span>➔</span>
              </Link>
            </div>

            {/* Bottom Trust Badges */}
            <div className="mt-6 pt-4 border-t border-[#DCE7F5] flex items-center justify-between text-[#657792] text-[11px] font-medium">
              <div className="flex items-center gap-1">
                <ShieldCheck className="w-3.5 h-3.5 text-[#087CF0]" />
                <span>AI Powered Protection</span>
              </div>
              <div className="flex items-center gap-1">
                <Lock className="w-3.5 h-3.5 text-[#087CF0]" />
                <span>Your Data Stays Secure</span>
              </div>
              <div className="flex items-center gap-1">
                <Heart className="w-3.5 h-3.5 text-[#EF4444]" />
                <span>Built for Everyone</span>
              </div>
            </div>

          </div>
        </div>

      </div>
    </div>
  );
};

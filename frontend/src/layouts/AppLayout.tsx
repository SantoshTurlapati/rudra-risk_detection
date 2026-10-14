import React, { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  Home, Search, ShieldCheck, Dna, Share2,
  Smartphone, Brain, Bell, Folder, FileText,
  Sparkles, Settings, ChevronDown, LogOut, Menu, X, ShieldAlert
} from 'lucide-react';
import { BrandLogo } from '../components/BrandLogo';
import { useAuth } from '../context/AuthContext';

export const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const navItems = [
    { name: 'Dashboard', path: '/dashboard', icon: Home },
    { name: 'Investigate', path: '/investigate', icon: Search },
    { name: 'Trusted Identity', path: '/trusted-identity', icon: ShieldCheck },
    { name: 'Scam DNA', path: '/scam-dna', icon: Dna },
    { name: 'Threat Graph', path: '/threat-graph', icon: Share2 },
    { name: 'App Analysis', path: '/app-analysis', icon: Smartphone },
    { name: 'Threat Intelligence', path: '/threat-intelligence', icon: Brain },
    { name: 'Critical Alerts', path: '/critical-alerts', icon: Bell },
    { name: 'Case History', path: '/case-history', icon: Folder },
    { name: 'Reports', path: '/reports', icon: FileText },
    { name: 'Safety Copilot', path: '/safety-copilot', icon: Sparkles },
    { name: 'Settings', path: '/settings', icon: Settings },
  ];

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/investigate?query=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex bg-[#F1F7FF] text-[#102447] font-sans antialiased">

      {/* ================= DARK NAVY SIDEBAR (REFERENCE A) ================= */}
      <aside className={`
        fixed inset-y-0 left-0 z-50 w-64 bg-[#041832] text-white flex flex-col justify-between
        transition-transform duration-200 ease-in-out lg:translate-x-0
        ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        {/* Brand Header */}
        <div>
          <div className="p-5 border-b border-[#0B2547] flex items-center justify-between">
            <BrandLogo size="md" variant="dark" />
            <button
              onClick={() => setMobileMenuOpen(false)}
              className="lg:hidden text-[#8E9EB5] hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <nav className="p-3 space-y-1 overflow-y-auto max-h-[calc(100vh-210px)]">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  onClick={() => setMobileMenuOpen(false)}
                  className={({ isActive }) => `
                    flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all
                    ${isActive
                      ? 'bg-gradient-to-r from-[#087CF0] to-[#06C8F9] text-white shadow-md shadow-blue-500/30'
                      : 'text-[#8E9EB5] hover:bg-[#082245] hover:text-white'
                    }
                  `}
                >
                  <div className="flex items-center gap-3">
                    <Icon className="w-4 h-4 flex-shrink-0" />
                    <span>{item.name}</span>
                  </div>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Sidebar Footer Banner Matching Reference A */}
        <div className="p-4 border-t border-[#0B2547]">
          <div className="bg-gradient-to-b from-[#08244B] to-[#04162E] p-3.5 rounded-2xl border border-[#0F356B] flex items-center gap-3 shadow-inner">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#087CF0] to-[#06C8F9] flex items-center justify-center flex-shrink-0 shadow-md">
              <ShieldCheck className="w-5 h-5 text-white" />
            </div>
            <div>
              <p className="text-[11px] font-bold text-white leading-tight">Together for a</p>
              <p className="text-[11px] font-medium text-cyan-300">Safer Digital World</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Backdrop for mobile */}
      {mobileMenuOpen && (
        <div
          onClick={() => setMobileMenuOpen(false)}
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
        />
      )}

      {/* ================= MAIN CONTENT WRAPPER ================= */}
      <div className="flex-1 flex flex-col min-w-0 lg:pl-64">

        {/* Top Header Bar Matching Reference A */}
        <header className="sticky top-0 z-30 bg-white border-b border-[#DCE7F5] h-16 flex items-center justify-between px-4 sm:px-6 shadow-sm">
          {/* Mobile menu trigger */}
          <div className="flex items-center gap-3 lg:hidden">
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="p-1.5 text-[#102447] hover:bg-[#F1F7FF] rounded-lg"
            >
              <Menu className="w-5 h-5" />
            </button>
            <BrandLogo size="sm" variant="light" showTagline={false} />
          </div>

          {/* Search Bar matching Reference A */}
          <form onSubmit={handleSearchSubmit} className="hidden sm:flex items-center flex-1 max-w-xl">
            <div className="relative w-full">
              <Search className="w-4 h-4 text-[#8E9EB5] absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by URL, profile, phone number, domain, message or upload file..."
                className="w-full pl-10 pr-4 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447] placeholder-[#8E9EB5] focus:outline-none focus:border-[#087CF0] focus:ring-1 focus:ring-[#087CF0]"
              />
            </div>
          </form>

          {/* Right Header Icons */}
          <div className="flex items-center gap-4">
            <span className="hidden md:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-50 border border-blue-200 text-[11px] font-semibold text-[#087CF0]">
              Heuristic Analysis
            </span>

            {/* Notification Bell */}
            <button
              onClick={() => navigate('/critical-alerts')}
              className="relative p-2 text-[#657792] hover:text-[#087CF0] hover:bg-[#F1F7FF] rounded-xl transition-colors"
            >
              <Bell className="w-5 h-5" />
            </button>

            <div className="relative">
              <button
                onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                className="flex items-center gap-2.5 p-1 hover:bg-[#F1F7FF] rounded-xl transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-[#061A3A] text-white font-bold text-xs flex items-center justify-center shadow-sm">
                  {user?.full_name?.[0] || user?.email?.[0] || '?'}
                </div>
                <div className="hidden sm:block text-left">
                  <p className="text-xs font-bold text-[#102447] leading-tight">
                    {user?.full_name || user?.email || 'Account unavailable'}
                  </p>
                  <p className="text-[10px] text-[#657792] font-medium leading-tight">
                    {user?.role || 'Role unavailable'}
                  </p>
                </div>
                <ChevronDown className="w-3.5 h-3.5 text-[#657792]" />
              </button>

              {/* User Dropdown */}
              {userDropdownOpen && (
                <div className="absolute right-0 mt-2 w-48 bg-white border border-[#DCE7F5] rounded-2xl shadow-xl py-2 z-50">
                  <div className="px-4 py-2 border-b border-[#DCE7F5]">
                    <p className="text-xs font-bold text-[#102447]">
                      {user?.full_name || user?.email || 'Account unavailable'}
                    </p>
                    <p className="text-[10px] text-[#657792]">{user?.email || 'Email unavailable'}</p>
                  </div>
                  <NavLink
                    to="/settings"
                    onClick={() => setUserDropdownOpen(false)}
                    className="block px-4 py-2 text-xs text-[#102447] hover:bg-[#F1F7FF]"
                  >
                    Settings & Profile
                  </NavLink>
                  <button
                    onClick={handleLogout}
                    className="w-full text-left px-4 py-2 text-xs text-red-600 hover:bg-red-50 flex items-center gap-2"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    Sign Out
                  </button>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Dynamic Route Outlet */}
        <main className="flex-1 p-4 sm:p-6 lg:p-7">
          <Outlet />
        </main>

        {/* Global Footer Matching Reference A */}
        <footer className="bg-white border-t border-[#DCE7F5] py-3.5 px-6 flex flex-col sm:flex-row items-center justify-between text-xs text-[#657792] gap-2">
          <div>
            <span className="font-semibold text-[#102447]">RudraShield AI</span> v1.0.0 &nbsp;|&nbsp;
            Powered by AI &nbsp;|&nbsp; Making the internet safer, together.
          </div>
          <div className="flex items-center gap-2 text-xs font-semibold text-emerald-600">
            <span className="w-2.5 h-2.5 rounded-full bg-[#12B981] inline-block animate-pulse" />
            System Online
          </div>
        </footer>

      </div>
    </div>
  );
};

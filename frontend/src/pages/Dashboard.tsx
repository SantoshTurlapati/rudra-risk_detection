import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ShieldCheck, AlertTriangle, Smartphone, UserX,
  ChevronRight, Globe, MessageSquare, ShieldAlert, Image, RefreshCw
} from 'lucide-react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import { api } from '../services/api';

const sparklinePoints = (values: number[]) => {
  const max = Math.max(...values, 1);
  return values.map((value, index) => {
    const x = index * (60 / Math.max(values.length - 1, 1));
    const y = 18 - (value / max) * 16;
    return `${x},${y}`;
  }).join(' ');
};

const relativeTime = (value?: string | null) => {
  if (!value) return 'Time unavailable';
  const timestamp = new Date(value).getTime();
  if (!Number.isFinite(timestamp)) return 'Time unavailable';

  const seconds = Math.floor((Date.now() - timestamp) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
};

type DashboardMetric = {
  value: number;
  trend: string;
  trend_label: string;
  sparkline: number[];
};

type RecentInvestigation = {
  id: string;
  type: string;
  indicator: string;
  risk_score: number | null;
  status: string;
  created_at: string | null;
};

type RecentCampaign = {
  id: string;
  name: string;
  description: string | null;
  related_entities_count: number;
  risk_level: string;
};

type RecentAlert = {
  id: string;
  title: string;
  description: string | null;
  severity: string;
  created_at: string | null;
};

type RecentActivity = { action: string; time: string; icon: string };

type DashboardStats = {
  metrics: Record<
    'total_investigations' | 'active_alerts' | 'suspicious_apps' | 'unresolved_profiles',
    DashboardMetric
  >;
  recent_investigations: RecentInvestigation[];
  recent_campaigns: RecentCampaign[];
  recent_alerts: RecentAlert[];
  india_heatmap: { top_affected_states: Array<{ state: string; threats: number }> };
  threat_categories: {
    total: number;
    distribution: Array<{ name: string; percentage: number; count: number; color: string }>;
  };
  recent_activity: RecentActivity[];
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const isRecentInvestigation = (value: unknown): value is RecentInvestigation =>
  isRecord(value)
  && typeof value.id === 'string'
  && typeof value.type === 'string'
  && typeof value.indicator === 'string'
  && (value.risk_score === null || (
    typeof value.risk_score === 'number' && Number.isFinite(value.risk_score)
  ))
  && typeof value.status === 'string'
  && (value.created_at === null || typeof value.created_at === 'string');

const isRecentCampaign = (value: unknown): value is RecentCampaign =>
  isRecord(value)
  && typeof value.id === 'string'
  && typeof value.name === 'string'
  && (value.description === null || typeof value.description === 'string')
  && typeof value.related_entities_count === 'number'
  && Number.isFinite(value.related_entities_count)
  && typeof value.risk_level === 'string';

const isRecentAlert = (value: unknown): value is RecentAlert =>
  isRecord(value)
  && typeof value.id === 'string'
  && typeof value.title === 'string'
  && (value.description === null || typeof value.description === 'string')
  && typeof value.severity === 'string'
  && (value.created_at === null || typeof value.created_at === 'string');

const isDashboardStats = (value: unknown): value is DashboardStats => {
  if (!isRecord(value) || !isRecord(value.metrics)) return false;
  const metrics = value.metrics;
  const metricNames = [
    'total_investigations',
    'active_alerts',
    'suspicious_apps',
    'unresolved_profiles',
  ] as const;
  const validMetrics = metricNames.every((name) => {
    const metric = metrics[name];
    return isRecord(metric)
      && typeof metric.value === 'number'
      && Number.isFinite(metric.value)
      && typeof metric.trend === 'string'
      && typeof metric.trend_label === 'string'
      && Array.isArray(metric.sparkline)
      && metric.sparkline.length === 7
      && metric.sparkline.every((count) =>
        typeof count === 'number' && Number.isFinite(count) && count >= 0);
  });
  if (!validMetrics || !Array.isArray(value.recent_investigations)
    || !value.recent_investigations.every(isRecentInvestigation)
    || !Array.isArray(value.recent_campaigns) || !value.recent_campaigns.every(isRecentCampaign)
    || !Array.isArray(value.recent_alerts) || !value.recent_alerts.every(isRecentAlert)
    || !Array.isArray(value.recent_activity) || !value.recent_activity.every((item) =>
      isRecord(item) && typeof item.action === 'string'
        && typeof item.time === 'string' && typeof item.icon === 'string')
    || !isRecord(value.india_heatmap)
    || !Array.isArray(value.india_heatmap.top_affected_states)
    || !value.india_heatmap.top_affected_states.every((item) =>
      isRecord(item) && typeof item.state === 'string'
        && typeof item.threats === 'number' && Number.isFinite(item.threats))
    || !isRecord(value.threat_categories)
    || typeof value.threat_categories.total !== 'number'
    || !Number.isFinite(value.threat_categories.total)
    || !Array.isArray(value.threat_categories.distribution)
    || !value.threat_categories.distribution.every((item) =>
      isRecord(item) && typeof item.name === 'string'
        && typeof item.percentage === 'number' && Number.isFinite(item.percentage)
        && typeof item.count === 'number' && Number.isFinite(item.count)
        && typeof item.color === 'string')) {
    return false;
  }
  return true;
};

const trendColor = (trend: string) => trend.startsWith('-')
  ? 'text-red-600'
  : trend === '0%' || trend === '—'
    ? 'text-[#657792]'
    : 'text-emerald-600';

export const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [investigations, setInvestigations] = useState<RecentInvestigation[]>([]);
  const [campaigns, setCampaigns] = useState<RecentCampaign[]>([]);
  const [alerts, setAlerts] = useState<RecentAlert[]>([]);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const dashData = await api.getDashboardStats();
      if (!isDashboardStats(dashData)) {
        throw new Error('Dashboard API response is incomplete.');
      }
      setStats(dashData);
      setInvestigations(dashData.recent_investigations);
      setCampaigns(dashData.recent_campaigns);
      setAlerts(dashData.recent_alerts);
    } catch (err) {
      console.error('Failed to load dashboard data', err);
      setError('Unable to load dashboard data. Please retry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const donutData = stats?.threat_categories.distribution.length
    ? stats.threat_categories.distribution
    : [];

  if (loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center rounded-2xl border border-[#DCE7F5] bg-white p-8 text-sm font-medium text-[#657792]">
        Loading dashboard data...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 rounded-2xl border border-red-200 bg-red-50 p-8 text-center text-sm text-red-700">
        <p>{error}</p>
        <button
          type="button"
          onClick={fetchData}
          className="rounded-xl bg-red-600 px-4 py-2 font-semibold text-white hover:bg-red-700"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">

      {/* ================= 1. CYBER WELCOME HERO BANNER (REF A) ================= */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-[#041832] via-[#062654] to-[#041832] border border-[#0F3B75] p-6 text-white shadow-lg">
        {/* Subtle Cyber Grid Background Overlay */}
        <div className="absolute inset-0 opacity-15 bg-[linear-gradient(to_right,#06C8F9_1px,transparent_1px),linear-gradient(to_bottom,#06C8F9_1px,transparent_1px)] bg-[size:24px_24px] pointer-events-none" />

        <div className="relative z-10 flex flex-col md:flex-row items-center justify-between gap-6">
          {/* Left: Glowing 3D Shield & Welcome Text */}
          <div className="flex items-center gap-5">
            <div className="relative flex-shrink-0">
              <div className="w-16 h-20 rounded-2xl bg-gradient-to-br from-[#06C8F9] via-[#0B8FFF] to-[#087CF0] p-0.5 shadow-[0_0_25px_rgba(6,200,249,0.5)] flex items-center justify-center">
                <div className="w-full h-full bg-[#041832] rounded-2xl flex items-center justify-center">
                  <ShieldCheck className="w-9 h-9 text-[#06C8F9] drop-shadow-[0_0_8px_rgba(6,200,249,0.8)]" />
                </div>
              </div>
            </div>

            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
                Welcome to <span className="text-[#06C8F9]">RudraShield AI</span>
              </h1>
              <p className="text-xs text-[#B8D3F5] mt-1 font-medium">
                Heuristic cyber threat indicators and evidence-based investigations
              </p>
              <div className="flex items-center gap-2 mt-2 text-[11px] text-cyan-300 font-semibold tracking-wide">
                <span>Analyze</span> • <span>Detect</span> • <span>Investigate</span> • <span>Stay Safe</span>
              </div>
            </div>
          </div>

          {/* Right: Hacker Quote Illustration */}
          <div className="hidden lg:flex items-center gap-4 bg-white/5 backdrop-blur-md px-5 py-3 rounded-2xl border border-white/10 shadow-inner">
            <div className="w-10 h-10 rounded-full bg-[#087CF0]/20 border border-[#06C8F9]/40 flex items-center justify-center">
              <ShieldAlert className="w-5 h-5 text-cyan-400" />
            </div>
            <div className="text-right">
              <p className="text-xs italic text-cyan-200 font-serif">
                “Be alert today, be safer tomorrow.”
              </p>
              <p className="text-[10px] text-[#8E9EB5] font-mono mt-0.5">Insights from recorded data</p>
            </div>
          </div>
        </div>
      </div>

      {/* ================= 2. FOUR STAT METRIC CARDS (REF A) ================= */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

        {/* Card 1: Total Investigations */}
        <div className="bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-xl bg-blue-50 text-[#087CF0] flex items-center justify-center">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <div className="text-right">
              <p className="text-xs font-semibold text-[#657792]">Total Investigations</p>
              <h3 className="text-2xl font-extrabold text-[#102447] mt-0.5">
                {stats?.metrics.total_investigations.value.toLocaleString() ?? '—'}
              </h3>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between pt-3 border-t border-[#F1F5F9]">
            <span className={`text-xs font-bold ${trendColor(stats?.metrics.total_investigations.trend ?? '—')}`}>
              {stats?.metrics.total_investigations.trend ?? '—'}
            </span>
            <span className="text-[11px] text-[#657792]">{stats?.metrics?.total_investigations?.trend_label}</span>
            <svg className="w-16 h-5" viewBox="0 0 60 20">
              <polyline points={sparklinePoints(stats?.metrics.total_investigations.sparkline ?? [])} fill="none" stroke="#087CF0" strokeWidth="2" />
            </svg>
          </div>
        </div>

        {/* Card 2: Active Alerts */}
        <div className="bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-xl bg-red-50 text-[#EF4444] flex items-center justify-center">
              <AlertTriangle className="w-5 h-5" />
            </div>
            <div className="text-right">
              <p className="text-xs font-semibold text-[#657792]">Active Alerts</p>
              <h3 className="text-2xl font-extrabold text-[#102447] mt-0.5">
                {stats?.metrics.active_alerts.value.toLocaleString() ?? '—'}
              </h3>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between pt-3 border-t border-[#F1F5F9]">
            <span className={`text-xs font-bold ${trendColor(stats?.metrics.active_alerts.trend ?? '—')}`}>
              {stats?.metrics.active_alerts.trend ?? '—'}
            </span>
            <span className="text-[11px] text-[#657792]">{stats?.metrics?.active_alerts?.trend_label}</span>
            <svg className="w-16 h-5" viewBox="0 0 60 20">
              <polyline points={sparklinePoints(stats?.metrics.active_alerts.sparkline ?? [])} fill="none" stroke="#EF4444" strokeWidth="2" />
            </svg>
          </div>
        </div>

        {/* Card 3: Suspicious Apps */}
        <div className="bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-xl bg-purple-50 text-[#8B5CF6] flex items-center justify-center">
              <Smartphone className="w-5 h-5" />
            </div>
            <div className="text-right">
              <p className="text-xs font-semibold text-[#657792]">Unresolved App Cases</p>
              <h3 className="text-2xl font-extrabold text-[#102447] mt-0.5">
                {stats?.metrics.suspicious_apps.value.toLocaleString() ?? '—'}
              </h3>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between pt-3 border-t border-[#F1F5F9]">
            <span className={`text-xs font-bold ${trendColor(stats?.metrics.suspicious_apps.trend ?? '—')}`}>
              {stats?.metrics.suspicious_apps.trend ?? '—'}
            </span>
            <span className="text-[11px] text-[#657792]">{stats?.metrics?.suspicious_apps?.trend_label}</span>
            <svg className="w-16 h-5" viewBox="0 0 60 20">
              <polyline points={sparklinePoints(stats?.metrics.suspicious_apps.sparkline ?? [])} fill="none" stroke="#8B5CF6" strokeWidth="2" />
            </svg>
          </div>
        </div>

        {/* Card 4: Unresolved Profile Cases */}
        <div className="bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card hover:shadow-card-hover transition-all">
          <div className="flex items-center justify-between">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 text-[#12B981] flex items-center justify-center">
              <UserX className="w-5 h-5" />
            </div>
            <div className="text-right">
              <p className="text-xs font-semibold text-[#657792]">Unresolved Profile Cases</p>
              <h3 className="text-2xl font-extrabold text-[#102447] mt-0.5">
                {stats?.metrics.unresolved_profiles.value.toLocaleString() ?? '—'}
              </h3>
            </div>
          </div>
          <div className="mt-4 flex items-center justify-between pt-3 border-t border-[#F1F5F9]">
            <span className={`text-xs font-bold ${trendColor(stats?.metrics.unresolved_profiles.trend ?? '—')}`}>
              {stats?.metrics.unresolved_profiles.trend ?? '—'}
            </span>
            <span className="text-[11px] text-[#657792]">{stats?.metrics?.unresolved_profiles?.trend_label}</span>
            <svg className="w-16 h-5" viewBox="0 0 60 20">
              <polyline points={sparklinePoints(stats?.metrics.unresolved_profiles.sparkline ?? [])} fill="none" stroke="#12B981" strokeWidth="2" />
            </svg>
          </div>
        </div>

      </div>

      {/* ================= 3. MIDDLE & RIGHT GRID (REF A) ================= */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Left 8 Columns (Heatmap, Categories Donut, Tables) */}
        <div className="lg:col-span-8 space-y-6">

          {/* Row 2.1: Threat Heatmap - India + Threat Categories Donut */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

            {/* Heatmap Card */}
            <div className="bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-bold text-[#102447] flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#087CF0]" />
                  Threat Locations
                </h3>
                <Link to="/threat-intelligence" className="text-xs font-semibold text-[#087CF0] hover:underline">
                  View All
                </Link>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 items-center">
                <div className="min-h-44 bg-[#F8FAFC] rounded-xl flex items-center justify-center p-4 border border-dashed border-[#DCE7F5] text-center text-xs text-[#657792]">
                  No geographic location data is available for recorded threats.
                </div>

                {/* Top Affected States Table */}
                <div className="space-y-2">
                  <p className="text-[11px] font-bold text-[#657792] uppercase tracking-wider">Top Affected States</p>
                  {stats?.india_heatmap?.top_affected_states?.length ? (
                    <div className="space-y-1.5 text-xs">
                      {stats.india_heatmap.top_affected_states.map((s: any) => (
                        <div key={s.state} className="flex items-center justify-between py-1 border-b border-gray-50">
                          <span className="text-[#102447] font-medium">{s.state}</span>
                          <span className="font-bold text-[#087CF0]">{s.threats}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="rounded-xl border border-dashed border-[#DCE7F5] bg-[#F8FAFC] p-4 text-xs text-[#657792]">
                      No geographic data available.
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Threat Categories Donut Card */}
            <div className="bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-bold text-[#102447] flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-[#06C8F9]" />
                  Threat Categories
                </h3>
              </div>

              <div className="flex items-center justify-between">
                {donutData.length > 0 ? (
                  <>
                    {/* Recharts Donut */}
                    <div className="w-36 h-36 relative flex items-center justify-center">
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={donutData}
                            innerRadius={42}
                            outerRadius={58}
                            paddingAngle={3}
                            dataKey="percentage"
                          >
                            {donutData.map((entry: any, index: number) => (
                              <Cell key={`cell-${index}`} fill={entry.color || '#DCE7F5'} />
                            ))}
                          </Pie>
                          <Tooltip />
                        </PieChart>
                      </ResponsiveContainer>
                      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                        <span className="text-sm font-extrabold text-[#102447]">{stats?.threat_categories.total ?? '—'}</span>
                        <span className="text-[10px] text-[#657792]">Total</span>
                      </div>
                    </div>

                    {/* Legend List matching Reference A */}
                    <div className="space-y-1.5 text-xs flex-1 pl-4">
                      {donutData.map((cat: any) => (
                        <div key={cat.name} className="flex items-center justify-between">
                          <div className="flex items-center gap-1.5">
                            <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: cat.color || '#DCE7F5' }} />
                            <span className="text-[#657792]">{cat.name}</span>
                          </div>
                          <span className="font-bold text-[#102447]">{cat.percentage}%</span>
                        </div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="w-full rounded-xl border border-dashed border-[#DCE7F5] bg-[#F8FAFC] p-6 text-center text-xs text-[#657792]">
                    No threat categories to report yet.
                  </div>
                )}
              </div>
            </div>

          </div>

          {/* Row 2.2: Recent Investigations Table (Ref A) */}
          <div className="bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-[#102447] flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#087CF0]" />
                Recent Investigations
              </h3>
              <Link to="/case-history" className="text-xs font-semibold text-[#087CF0] hover:underline">
                View All
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#DCE7F5] text-[#657792] pb-2 font-semibold">
                    <th className="py-2.5 px-3">Type</th>
                    <th className="py-2.5 px-3">Indicator</th>
                    <th className="py-2.5 px-3">Risk Score</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Time</th>
                    <th className="py-2.5 px-2"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 font-medium">
                  {investigations.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-sm text-[#657792]">
                        No investigations yet. Start your first analysis.
                      </td>
                    </tr>
                  ) : investigations.map((inv) => (
                    <tr key={inv.id} className="hover:bg-[#F8FAFC] transition-colors">
                      <td className="py-3 px-3 flex items-center gap-2">
                        {inv.type === 'Website' || inv.type === 'website' ? <Globe className="w-3.5 h-3.5 text-blue-500" /> :
                         inv.type === 'Social Profile' || inv.type === 'social_profile' ? <UserX className="w-3.5 h-3.5 text-emerald-500" /> :
                         inv.type === 'Mobile App' || inv.type === 'mobile_app' ? <Smartphone className="w-3.5 h-3.5 text-purple-500" /> :
                         <MessageSquare className="w-3.5 h-3.5 text-orange-500" />}
                        <span className="text-[#102447]">{inv.type}</span>
                      </td>
                      <td className="py-3 px-3 font-mono text-[#087CF0]">{inv.indicator}</td>
                      <td className="py-3 px-3">
                        <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                          inv.risk_score == null ? 'bg-gray-100 text-gray-600' :
                          inv.risk_score >= 80 ? 'bg-red-100 text-red-600' :
                          inv.risk_score >= 50 ? 'bg-orange-100 text-orange-600' :
                          'bg-emerald-100 text-emerald-600'
                        }`}>
                          {inv.risk_score ?? 'Not assessed'}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-semibold ${
                          inv.status === 'Malicious' ? 'bg-red-50 text-red-600 border border-red-200' :
                          inv.status === 'Suspicious' ? 'bg-orange-50 text-orange-600 border border-orange-200' :
                          inv.status === 'Phishing' ? 'bg-purple-50 text-purple-600 border border-purple-200' :
                          'bg-teal-50 text-teal-600 border border-teal-200'
                        }`}>
                          {inv.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 text-[#8E9EB5]">{relativeTime(inv.created_at)}</td>
                      <td className="py-3 px-2 text-right">
                        <button
                          onClick={() => navigate(`/case-history?id=${inv.id}`)}
                          className="text-[#657792] hover:text-[#087CF0]"
                        >
                          <ChevronRight className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Row 2.3: Scam Campaigns Table (Ref A) */}
          <div className="bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-[#102447] flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-[#8B5CF6]" />
                Scam Campaigns
              </h3>
              <Link to="/threat-intelligence" className="text-xs font-semibold text-[#087CF0] hover:underline">
                View All
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-[#DCE7F5] text-[#657792] font-semibold">
                    <th className="py-2 px-3">Campaign</th>
                    <th className="py-2 px-3">Related Entities</th>
                    <th className="py-2 px-3">Risk Level</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {campaigns.length === 0 ? (
                    <tr>
                      <td colSpan={3} className="py-6 text-center text-sm text-[#657792]">
                        No campaigns supported by current evidence.
                      </td>
                    </tr>
                  ) : campaigns.map((camp) => (
                    <tr key={camp.id} className="hover:bg-[#F8FAFC]">
                      <td className="py-3 px-3">
                        <p className="font-bold text-[#102447]">{camp.name}</p>
                        <p className="text-[11px] text-[#657792]">{camp.description}</p>
                      </td>
                      <td className="py-3 px-3 font-semibold text-[#102447]">
                        {camp.related_entities_count}
                      </td>
                      <td className="py-3 px-3">
                        <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                          camp.risk_level === 'High' ? 'bg-red-100 text-red-600' : 'bg-orange-100 text-orange-600'
                        }`}>
                          {camp.risk_level}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

        </div>

        {/* Right 4 Columns (Critical Alerts, Quick Actions, Recent Activity) */}
        <div className="lg:col-span-4 space-y-6">

          {/* Critical Alerts Card matching Reference A */}
          <div className="bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-[#102447] flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-[#EF4444]" />
                Active Alerts
              </h3>
              <Link to="/critical-alerts" className="text-xs font-semibold text-[#087CF0] hover:underline">
                View All
              </Link>
            </div>

            <div className="space-y-3">
              {alerts.length === 0 ? (
                <div className="rounded-xl border border-dashed border-[#DCE7F5] bg-[#F8FAFC] p-4 text-center text-xs text-[#657792]">
                  No active alerts are recorded.
                </div>
              ) : alerts.map((alt) => (
                <div key={alt.id} className="p-3 rounded-xl bg-[#F8FAFC] border border-[#E2E8F0] hover:border-blue-200 transition-colors">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-xs font-bold text-[#102447]">{alt.title}</p>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex-shrink-0 ${
                      alt.severity === 'High' ? 'bg-red-100 text-red-600' : 'bg-orange-100 text-orange-600'
                    }`}>
                      {alt.severity}
                    </span>
                  </div>
                  <p className="text-[11px] text-[#657792] font-mono mt-1">{alt.description}</p>
                  <p className="text-[10px] text-[#8E9EB5] mt-1.5">{relativeTime(alt.created_at)}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Actions Card matching Reference A */}
          <div className="bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card">
            <h3 className="text-sm font-bold text-[#102447] flex items-center gap-2 mb-4">
              <ShieldCheck className="w-4 h-4 text-[#087CF0]" />
              Quick Actions
            </h3>

            <div className="grid grid-cols-2 gap-2.5">
              <button
                onClick={() => navigate('/investigate?tab=url')}
                className="p-3 rounded-xl bg-[#F0F7FF] hover:bg-[#E1EFFF] text-left border border-[#D0E4FA] transition-all"
              >
                <Globe className="w-4 h-4 text-[#087CF0] mb-1.5" />
                <p className="text-xs font-bold text-[#102447]">Analyze a URL</p>
                <p className="text-[10px] text-[#657792]">Check website safety</p>
              </button>

              <button
                onClick={() => navigate('/investigate?tab=profile')}
                className="p-3 rounded-xl bg-[#F0F7FF] hover:bg-[#E1EFFF] text-left border border-[#D0E4FA] transition-all"
              >
                <UserX className="w-4 h-4 text-[#087CF0] mb-1.5" />
                <p className="text-xs font-bold text-[#102447]">Check a Profile</p>
                <p className="text-[10px] text-[#657792]">Verify social media</p>
              </button>

              <button
                onClick={() => navigate('/investigate?tab=image')}
                className="p-3 rounded-xl bg-[#F0F7FF] hover:bg-[#E1EFFF] text-left border border-[#D0E4FA] transition-all"
              >
                <Image className="w-4 h-4 text-[#087CF0] mb-1.5" />
                <p className="text-xs font-bold text-[#102447]">Analyze an Image</p>
                <p className="text-[10px] text-[#657792]">Compute a candidate image hash</p>
              </button>

              <button
                onClick={() => navigate('/investigate?tab=message')}
                className="p-3 rounded-xl bg-[#F0F7FF] hover:bg-[#E1EFFF] text-left border border-[#D0E4FA] transition-all"
              >
                <MessageSquare className="w-4 h-4 text-[#087CF0] mb-1.5" />
                <p className="text-xs font-bold text-[#102447]">Scan a Message</p>
                <p className="text-[10px] text-[#657792]">Check for scams</p>
              </button>
            </div>
          </div>

          {/* Recent Activity Card matching Reference A */}
          <div className="bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-[#102447] flex items-center gap-2">
                <RefreshCw className="w-4 h-4 text-[#087CF0]" />
                Recent Activity
              </h3>
              <Link to="/case-history" className="text-xs font-semibold text-[#087CF0] hover:underline">
                View All
              </Link>
            </div>

            <div className="space-y-3 text-xs">
              {stats?.recent_activity?.length ? stats.recent_activity.map((act: any, idx: number) => (
                <div key={idx} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-none">
                  <span className="text-[#102447] font-medium pr-2">{act.action}</span>
                  <span className="text-[10px] text-[#8E9EB5] whitespace-nowrap">{act.time}</span>
                </div>
              )) : (
                <div className="rounded-xl border border-dashed border-[#DCE7F5] bg-[#F8FAFC] p-4 text-center text-xs text-[#657792]">
                  No recent activity yet.
                </div>
              )}
            </div>
          </div>

        </div>

      </div>

    </div>
  );
};

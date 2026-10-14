import React, { useEffect, useState } from 'react';
import {
  Bell, AlertTriangle, CheckCircle2, Clock,
  ShieldAlert, Check, X, Filter
} from 'lucide-react';
import { api } from '../services/api';
import { Alert } from '../types';

export const CriticalAlerts: React.FC = () => {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filterSeverity, setFilterSeverity] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');
  const [loading, setLoading] = useState(true);

  const fetchAlerts = async () => {
    try {
      const data = await api.getAlerts();
      setAlerts(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  const handleUpdateStatus = async (id: string, status: string) => {
    try {
      await api.updateAlert(id, status);
      fetchAlerts();
    } catch (err) {
      console.error(err);
    }
  };

  const filtered = alerts.filter(a => {
    const matchSev = filterSeverity === 'all' || a.severity.toLowerCase() === filterSeverity.toLowerCase();
    const matchStat = filterStatus === 'all' || a.status.toLowerCase() === filterStatus.toLowerCase();
    return matchSev && matchStat;
  });

  return (
    <div className="space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[#102447] flex items-center gap-2">
          <Bell className="w-5 h-5 text-[#EF4444]" />
          Critical Threat Alerts
        </h1>
        <p className="text-xs text-[#657792] mt-0.5">
          Current alert queue for severe stored brand impersonations, suspicious app findings, and active case escalations
        </p>
      </div>

      {/* Filter Row */}
      <div className="bg-white p-4 rounded-2xl border border-[#DCE7F5] flex flex-wrap items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2 text-xs">
            <span className="font-bold text-[#657792]">Severity:</span>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value)}
              className="px-3 py-1.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl font-semibold"
            >
              <option value="all">All</option>
              <option value="critical">Critical</option>
              <option value="high">High</option>
              <option value="medium">Medium</option>
            </select>
          </div>

          <div className="flex items-center gap-2 text-xs">
            <span className="font-bold text-[#657792]">Status:</span>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className="px-3 py-1.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl font-semibold"
            >
              <option value="all">All</option>
              <option value="unread">Unread</option>
              <option value="acknowledged">Acknowledged</option>
              <option value="resolved">Resolved</option>
            </select>
          </div>
        </div>

        <div className="text-xs font-semibold text-[#087CF0]">
          Total Alerts: {alerts.length}
        </div>
      </div>

      {/* Alerts List */}
      <div className="space-y-3">
        {filtered.map((alt) => (
          <div
            key={alt.id}
            className={`p-5 rounded-2xl border transition-all ${
              alt.status === 'Resolved'
                ? 'bg-gray-50 border-gray-200 opacity-75'
                : 'bg-white border-[#DCE7F5] shadow-card hover:border-blue-300'
            }`}
          >
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-start gap-3">
                <div className={`w-9 h-9 rounded-xl flex items-center justify-center flex-shrink-0 mt-0.5 ${
                  alt.severity === 'Critical' || alt.severity === 'High'
                    ? 'bg-red-50 text-red-600'
                    : 'bg-amber-50 text-amber-600'
                }`}>
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-[#102447]">{alt.title}</h3>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-extrabold ${
                      alt.severity === 'High' || alt.severity === 'Critical'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-orange-100 text-orange-700'
                    }`}>
                      {alt.severity}
                    </span>
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                      alt.status === 'Resolved' ? 'bg-emerald-100 text-emerald-700' :
                      alt.status === 'Acknowledged' ? 'bg-blue-100 text-blue-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {alt.status}
                    </span>
                  </div>
                  <p className="text-xs text-[#657792] font-mono mt-1">{alt.description}</p>
                  <p className="text-[10px] text-[#8E9EB5] mt-1 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> {new Date(alt.created_at).toLocaleString()} • Source: {alt.source}
                  </p>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 self-end sm:self-center">
                {alt.status !== 'Acknowledged' && alt.status !== 'Resolved' && (
                  <button
                    onClick={() => handleUpdateStatus(alt.id, 'Acknowledged')}
                    className="px-3 py-1.5 bg-[#F1F7FF] text-[#087CF0] hover:bg-[#E1EFFF] text-xs font-bold rounded-xl transition-colors"
                  >
                    Acknowledge
                  </button>
                )}
                {alt.status !== 'Resolved' && (
                  <button
                    onClick={() => handleUpdateStatus(alt.id, 'Resolved')}
                    className="px-3 py-1.5 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 text-xs font-bold rounded-xl transition-colors"
                  >
                    Resolve
                  </button>
                )}
                {alt.status === 'Resolved' && (
                  <button
                    onClick={() => handleUpdateStatus(alt.id, 'Unread')}
                    className="px-3 py-1.5 bg-gray-100 text-gray-700 hover:bg-gray-200 text-xs font-bold rounded-xl transition-colors"
                  >
                    Reopen
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
};

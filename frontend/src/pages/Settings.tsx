import React, { useEffect, useState } from 'react';
import {
  Settings as SettingsIcon, User, Building, Cpu, History
} from 'lucide-react';
import { api } from '../services/api';

export const SettingsPage: React.FC = () => {
  const [settingsData, setSettingsData] = useState<any>(null);
  const [settingsError, setSettingsError] = useState('');
  const [activeTab, setActiveTab] = useState<'profile' | 'integrations' | 'engine' | 'audit'>('profile');

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const data = await api.getSettings();
        setSettingsData(data);
      } catch (err) {
        console.error(err);
        setSettingsError('Settings could not be loaded. Refresh the page and try again.');
      }
    };
    fetchSettings();
  }, []);

  return (
    <div className="space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[#102447] flex items-center gap-2">
          <SettingsIcon className="w-5 h-5 text-[#087CF0]" />
          Platform Settings &amp; Integrations
        </h1>
        <p className="text-xs text-[#657792] mt-0.5">
          Manage user profiles, brand intelligence connectors, heuristic engine configuration, and audit logs
        </p>
      </div>
      {settingsError && (
        <p role="alert" className="p-3 bg-red-50 text-red-700 rounded-xl text-xs">
          {settingsError}
        </p>
      )}

      {/* Navigation Tabs */}
      <div className="flex border-b border-[#DCE7F5] gap-6 text-xs font-bold">
        <button
          onClick={() => setActiveTab('profile')}
          className={`pb-3 transition-colors ${activeTab === 'profile' ? 'text-[#087CF0] border-b-2 border-[#087CF0]' : 'text-[#657792] hover:text-[#102447]'}`}
        >
          User &amp; Organization
        </button>
        <button
          onClick={() => setActiveTab('integrations')}
          className={`pb-3 transition-colors ${activeTab === 'integrations' ? 'text-[#087CF0] border-b-2 border-[#087CF0]' : 'text-[#657792] hover:text-[#102447]'}`}
        >
          API Connectors &amp; Social Feeds
        </button>
        <button
          onClick={() => setActiveTab('engine')}
          className={`pb-3 transition-colors ${activeTab === 'engine' ? 'text-[#087CF0] border-b-2 border-[#087CF0]' : 'text-[#657792] hover:text-[#102447]'}`}
        >
          AI Detection Engines
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          className={`pb-3 transition-colors ${activeTab === 'audit' ? 'text-[#087CF0] border-b-2 border-[#087CF0]' : 'text-[#657792] hover:text-[#102447]'}`}
        >
          Security Audit Logs
        </button>
      </div>

      {/* Tab: Profile */}
      {activeTab === 'profile' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white p-6 rounded-2xl border border-[#DCE7F5] shadow-card space-y-4">
            <h3 className="text-sm font-bold text-[#102447] flex items-center gap-2">
              <User className="w-4 h-4 text-[#087CF0]" />
              Active Analyst Profile
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <p className="text-[10px] text-[#657792] uppercase font-bold">Full Name</p>
                <p className="font-bold text-[#102447] text-sm mt-0.5">{settingsData?.user_profile?.full_name || 'Not available'}</p>
              </div>
              <div>
                <p className="text-[10px] text-[#657792] uppercase font-bold">Role / Access Level</p>
                <span className="px-2.5 py-0.5 rounded-full bg-blue-50 text-[#087CF0] font-bold text-[11px] inline-block mt-0.5">
                  {settingsData?.user_profile?.role || 'Not available'}
                </span>
              </div>
              <div>
                <p className="text-[10px] text-[#657792] uppercase font-bold">Email Address</p>
                <p className="font-mono text-[#102447] mt-0.5">{settingsData?.user_profile?.email || 'Not available'}</p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-2xl border border-[#DCE7F5] shadow-card space-y-4">
            <h3 className="text-sm font-bold text-[#102447] flex items-center gap-2">
              <Building className="w-4 h-4 text-[#087CF0]" />
              Organization Deployment
            </h3>
            <div className="space-y-3 text-xs">
              <div>
                <p className="text-[10px] text-[#657792] uppercase font-bold">Organization Name</p>
                <p className="font-bold text-[#102447] mt-0.5">{settingsData?.organization?.name || 'Not assigned'}</p>
              </div>
              <div>
                <p className="text-[10px] text-[#657792] uppercase font-bold">Active Members</p>
                <p className="font-semibold text-[#102447] mt-0.5">{settingsData?.organization?.active_seats ?? 'Not available'}</p>
              </div>
              <div>
                <p className="text-[10px] text-[#657792] uppercase font-bold">Database Engine</p>
                <p className="text-[#657792] mt-0.5">{settingsData?.organization?.database_engine || 'Not available'}</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Integrations */}
      {activeTab === 'integrations' && (
        <div className="bg-white p-6 rounded-2xl border border-[#DCE7F5] shadow-card space-y-4">
          <h3 className="text-sm font-bold text-[#102447]">Platform Connectors</h3>
          <p className="text-xs text-[#657792]">
            Configured external providers will appear here. No external integrations are currently configured.
          </p>

          <div className="space-y-3">
            {!settingsData ? (
              <p className="py-6 text-center text-xs text-[#657792]">
                {settingsError ? 'Integration data is unavailable.' : 'Loading integrations...'}
              </p>
            ) : (settingsData.integrations || []).length === 0 ? (
              <p className="py-6 text-center text-xs text-[#657792]">No integrations configured.</p>
            ) : settingsData.integrations.map((integ: any, i: number) => (
              <div key={i} className="p-3.5 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] flex items-center justify-between text-xs">
                <div>
                  <p className="font-bold text-[#102447]">{integ.provider}</p>
                  <p className="text-[11px] text-[#657792]">{integ.status}</p>
                </div>
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                  integ.connected ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'
                }`}>
                  {integ.connected ? 'Connected' : 'Offline'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Engine */}
      {activeTab === 'engine' && (
        <div className="bg-white p-6 rounded-2xl border border-[#DCE7F5] shadow-card space-y-4">
          <h3 className="text-sm font-bold text-[#102447] flex items-center gap-2">
            <Cpu className="w-4 h-4 text-[#087CF0]" />
            Detection Engine Configuration
          </h3>

          {!settingsData ? (
            <p className="py-6 text-center text-xs text-[#657792]">
              {settingsError ? 'Engine details are unavailable.' : 'Loading engine details...'}
            </p>
          ) : Object.entries(settingsData.detection_engine || {}).length === 0 ? (
            <p className="py-6 text-center text-xs text-[#657792]">Engine details are unavailable.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              {Object.entries(settingsData.detection_engine).map(([name, description]) => (
                <div key={name} className="p-4 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl space-y-1">
                  <p className="font-bold text-[#102447]">{name.replace(/_/g, ' ')}</p>
                  <p className="text-[#657792]">{String(description)}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Tab: Audit */}
      {activeTab === 'audit' && (
        <div className="bg-white p-6 rounded-2xl border border-[#DCE7F5] shadow-card space-y-4">
          <h3 className="text-sm font-bold text-[#102447] flex items-center gap-2">
            <History className="w-4 h-4 text-[#087CF0]" />
            System Audit Log
          </h3>

          <div className="space-y-2 text-xs">
            {!settingsData ? (
              <p className="py-6 text-center text-xs text-[#657792]">
                {settingsError ? 'Audit events are unavailable.' : 'Loading audit events...'}
              </p>
            ) : settingsData.audit_logs.length === 0 ? (
              <p className="py-6 text-center text-xs text-[#657792]">No audit events recorded for this organization.</p>
            ) : settingsData.audit_logs.map((log: any, i: number) => (
              <div key={i} className="p-3 bg-[#F8FAFC] border border-gray-100 rounded-xl flex items-center justify-between">
                <div>
                  <p className="font-bold text-[#102447]">{log.action}</p>
                  <p className="text-[11px] text-[#657792]">User: {log.user}</p>
                  {log.details?.previous_status !== undefined && (
                    <p className="text-[11px] text-[#657792]">
                      Brand status: {log.details.previous_status ? 'Admin-marked verified' : 'Unverified'}
                      {' → '}
                      {log.details.new_status ? 'Admin-marked verified' : 'Unverified'}
                    </p>
                  )}
                </div>
                <span className="text-[11px] text-[#8E9EB5]">
                  {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'Time unavailable'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
};

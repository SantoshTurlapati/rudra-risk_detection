import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Folder, Search, Filter, ChevronRight, Edit3,
  Check, X, FileText, Download, AlertTriangle
} from 'lucide-react';
import { api } from '../services/api';
import { Investigation } from '../types';

export const CaseHistory: React.FC = () => {
  const [searchParams] = useSearchParams();
  const highlightId = searchParams.get('id');

  const [cases, setCases] = useState<Investigation[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCase, setSelectedCase] = useState<Investigation | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [analystNotes, setAnalystNotes] = useState('');
  const [statusVal, setStatusVal] = useState('');
  const [dispositionReason, setDispositionReason] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');

  const fetchCases = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getInvestigations();
      setCases(data);
      if (highlightId) {
        const found = data.find(c => c.id === highlightId || c.case_number === highlightId);
        if (found) {
          openDetailModal(found);
        }
      }
    } catch (err) {
      console.error(err);
      setError('Investigation history could not be loaded. Please retry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [highlightId]);

  const openDetailModal = (c: Investigation) => {
    setSelectedCase(c);
    setAnalystNotes(c.analyst_notes || '');
    setStatusVal(c.status);
    setDispositionReason('');
    setModalOpen(true);
  };

  const handleUpdateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCase) return;
    setSaving(true);
    setError('');
    try {
      await api.updateInvestigation(selectedCase.id, {
        analyst_notes: analystNotes,
        status: statusVal,
        disposition_reason: statusVal === 'False Positive' ? dispositionReason : undefined,
      });
      setModalOpen(false);
      await fetchCases();
    } catch (err) {
      console.error(err);
      setError('The case changes could not be saved. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleDownload = async () => {
    if (!selectedCase) return;
    setDownloading(true);
    setError('');
    try {
      const blob = await api.downloadReport(selectedCase.case_number);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `RudraShield_${selectedCase.case_number}_Report.csv`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      console.error('Case report download failed', err);
      setError('The case report could not be downloaded. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  const findings = selectedCase?.findings_json;
  const savedEvidence = Array.isArray(findings?.findings)
    ? findings.findings
    : Array.isArray(findings?.evidence)
      ? findings.evidence
      : [];
  const reviewHistory = Array.isArray(findings?._review_history)
    ? findings._review_history as Array<{
      recorded_at?: string;
      recorded_by_user_id?: string;
      disposition_reason?: string | null;
      changes?: Record<string, { previous?: unknown; new?: unknown; changed?: boolean }>;
    }>
    : [];

  const filtered = cases.filter(c =>
    c.case_number.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.indicator.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[#102447] flex items-center gap-2">
          <Folder className="w-5 h-5 text-[#087CF0]" />
          Investigation Case History
        </h1>
        <p className="text-xs text-[#657792] mt-0.5">
          Archived and ongoing brand defense cases, evidence packages, and analyst dispositions
        </p>
      </div>

      {error && (
        <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
          <span>{error}</span>
          {!modalOpen && (
            <button type="button" onClick={fetchCases} className="font-bold underline">
              Retry
            </button>
          )}
        </div>
      )}

      {/* Search and Filters */}
      <div className="bg-white p-4 rounded-2xl border border-[#DCE7F5] flex items-center justify-between gap-4 shadow-sm">
        <div className="relative w-full max-w-md">
          <Search className="w-4 h-4 text-[#8E9EB5] absolute left-3.5 top-3" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by case ID or indicator..."
            className="w-full pl-10 pr-4 py-2.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447] focus:outline-none focus:border-[#087CF0]"
          />
        </div>

        <span className="text-xs font-bold text-[#657792]">
          Total Cases: {cases.length}
        </span>
      </div>

      {loading ? (
        <div role="status" className="rounded-2xl border border-[#DCE7F5] bg-white p-8 text-center text-sm text-[#657792]">
          Loading investigation history...
        </div>
      ) : (
      /* Case Table */
      <div className="bg-white rounded-2xl border border-[#DCE7F5] shadow-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-[#F8FAFC] border-b border-[#DCE7F5] text-[#657792] font-semibold">
              <tr>
                <th className="py-3 px-4">Case ID</th>
                <th className="py-3 px-4">Target Indicator</th>
                <th className="py-3 px-4">Modality</th>
                <th className="py-3 px-4">Risk Score</th>
                <th className="py-3 px-4">Severity</th>
                <th className="py-3 px-4">Disposition Status</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 font-medium">
              {filtered.map((c) => (
                <tr key={c.id} className="hover:bg-[#F8FAFC] transition-colors">
                  <td className="py-3.5 px-4 font-mono font-bold text-[#087CF0]">{c.case_number}</td>
                  <td className="py-3.5 px-4 font-mono text-[#102447] max-w-xs truncate">{c.indicator}</td>
                  <td className="py-3.5 px-4 text-[#657792]">{c.type}</td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                      c.risk_score == null ? 'bg-gray-100 text-gray-700' :
                      c.risk_score >= 80 ? 'bg-red-100 text-red-700' :
                      c.risk_score >= 50 ? 'bg-orange-100 text-orange-700' :
                      'bg-emerald-100 text-emerald-700'
                    }`}>
                      {c.risk_score == null ? 'Not assessed' : `${c.risk_score}/100`}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                      c.severity === 'Critical' ? 'bg-red-100 text-red-700' :
                      c.severity === 'High' ? 'bg-orange-100 text-orange-700' :
                      'bg-gray-100 text-gray-700'
                    }`}>
                      {c.severity}
                    </span>
                  </td>
                  <td className="py-3.5 px-4">
                    <span className="px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-[#087CF0] border border-blue-200">
                      {c.status}
                    </span>
                  </td>
                  <td className="py-3.5 px-4 text-[#8E9EB5]">
                    {new Date(c.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <button
                      onClick={() => openDetailModal(c)}
                      className="px-3 py-1.5 bg-[#F1F7FF] hover:bg-[#E1EFFF] text-[#087CF0] rounded-xl text-xs font-bold transition-colors"
                    >
                      Inspect Case
                    </button>
                  </td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={8} className="py-10 text-center text-xs text-[#657792]">
                    {cases.length === 0 ? 'No investigations are recorded for this organization.' : 'No cases match this search.'}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
      )}

      {/* Case Details Modal */}
      {modalOpen && selectedCase && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-[#DCE7F5] max-h-[90vh] overflow-y-auto space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#DCE7F5]">
              <div>
                <span className="font-mono text-xs font-bold text-[#087CF0]">{selectedCase.case_number}</span>
                <h3 className="text-base font-bold text-[#102447]">Case Investigation Dossier</h3>
              </div>
              <button onClick={() => setModalOpen(false)} className="text-[#657792]">
                <X className="w-5 h-5" />
              </button>
            </div>

            {error && <p role="alert" className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">{error}</p>}

            <div className="space-y-3 text-xs">
              <div>
                <p className="text-[10px] font-bold text-[#657792] uppercase">Target Indicator</p>
                <p className="font-mono font-bold text-sm text-[#102447] mt-0.5 break-all">{selectedCase.indicator}</p>
              </div>

              <div className="grid grid-cols-2 gap-3 p-3 bg-[#F8FAFC] rounded-xl border border-[#DCE7F5]">
                <div>
                  <p className="text-[10px] font-bold text-[#657792]">Risk Score</p>
                  <p className="text-base font-black text-red-600">
                    {selectedCase.risk_score == null ? 'Not assessed' : `${selectedCase.risk_score}/100`}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-[#657792]">Stored Confidence (Provenance Unknown)</p>
                  <p className="text-base font-black text-[#087CF0]">
                    {selectedCase.confidence == null ? 'Not assessed' : `${selectedCase.confidence}%`}
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <p className="text-[10px] font-bold text-[#657792] uppercase">Modality</p>
                  <p className="font-semibold text-[#102447]">{selectedCase.type}</p>
                </div>
                <div>
                  <p className="text-[10px] font-bold text-[#657792] uppercase">Recorded</p>
                  <p className="font-semibold text-[#102447]">{new Date(selectedCase.created_at).toLocaleString()}</p>
                </div>
              </div>

              <div>
                <p className="text-[10px] font-bold text-[#657792] uppercase mb-1.5">Saved Findings</p>
                {savedEvidence.length > 0 ? (
                  <ul className="list-disc space-y-1 pl-4 text-[#334155]">
                    {savedEvidence.map((item, index) => (
                      <li key={index}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-[#657792]">No findings were saved with this case.</p>
                )}
              </div>

              {findings?._record_provenance && (
                <div className="rounded-xl border border-blue-100 bg-blue-50 p-3">
                  <p className="text-[10px] font-bold text-[#657792] uppercase">Record Provenance</p>
                  <p className="mt-1 text-[#334155]">
                    {findings._record_provenance.source_attribution || 'Submission source is not specified.'}
                  </p>
                  <p className="mt-1 text-[10px] text-[#657792]">
                    Recorded {findings._record_provenance.recorded_at
                      ? new Date(findings._record_provenance.recorded_at).toLocaleString()
                      : 'time unavailable'}
                  </p>
                </div>
              )}

              <div className="space-y-2">
                <p className="text-[10px] font-bold text-[#657792] uppercase">Review History</p>
                {reviewHistory.length === 0 ? (
                  <p className="text-[#657792]">No analyst review changes are recorded.</p>
                ) : reviewHistory.map((entry, index) => (
                  <div key={`${entry.recorded_at || 'event'}-${index}`} className="rounded-lg border border-[#DCE7F5] bg-[#F8FAFC] p-2.5">
                    <p className="font-semibold text-[#102447]">
                      {entry.changes?.status
                        ? `Status: ${String(entry.changes.status.previous)} → ${String(entry.changes.status.new)}`
                        : 'Case details updated'}
                    </p>
                    {entry.disposition_reason && (
                      <p className="mt-1 text-[#334155]">Reason: {entry.disposition_reason}</p>
                    )}
                    <p className="mt-1 text-[10px] text-[#657792]">
                      {entry.recorded_at ? new Date(entry.recorded_at).toLocaleString() : 'Time unavailable'}
                    </p>
                  </div>
                ))}
              </div>

              <form onSubmit={handleUpdateCase} className="space-y-3 pt-2">
                <div>
                  <label className="text-xs font-bold text-[#102447]">Case Status Disposition</label>
                  <select
                    value={statusVal}
                    onChange={(e) => setStatusVal(e.target.value)}
                    className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl font-semibold mt-1"
                  >
                    <option>Malicious</option>
                    <option>Suspicious</option>
                    <option>Phishing</option>
                    <option>Low Risk</option>
                    <option>Safe</option>
                    <option>False Positive</option>
                    <option>Resolved</option>
                    <option>Under Review</option>
                  </select>
                </div>

                {statusVal === 'False Positive' && (
                  <div>
                    <label className="text-xs font-bold text-[#102447]" htmlFor="false-positive-reason">
                      False-positive review reason
                    </label>
                    <textarea
                      id="false-positive-reason"
                      rows={2}
                      required
                      value={dispositionReason}
                      onChange={(e) => setDispositionReason(e.target.value)}
                      placeholder="Explain the evidence behind this disposition."
                      className="w-full p-3 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs mt-1"
                    />
                  </div>
                )}

                <div>
                  <label className="text-xs font-bold text-[#102447]">Analyst Disposition Notes</label>
                  <textarea
                    rows={3}
                    value={analystNotes}
                    onChange={(e) => setAnalystNotes(e.target.value)}
                    placeholder="Enter investigative conclusions, takedown notes, or law enforcement referrals..."
                    className="w-full p-3 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs mt-1"
                  />
                </div>

                <div className="flex justify-between items-center pt-2">
                  <button
                    type="button"
                    onClick={handleDownload}
                    disabled={downloading}
                    className="px-3 py-2 border border-[#DCE7F5] hover:bg-gray-50 text-[#102447] rounded-xl text-xs font-bold flex items-center gap-1.5 disabled:opacity-60"
                  >
                    <Download className="w-3.5 h-3.5 text-[#087CF0]" />
                    {downloading ? 'Preparing CSV...' : 'Export CSV'}
                  </button>

                  <button
                    type="submit"
                    disabled={saving}
                    className="px-4 py-2 bg-[#087CF0] hover:bg-[#076ecc] text-white rounded-xl text-xs font-bold shadow-md"
                  >
                    {saving ? 'Saving...' : 'Save Changes'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

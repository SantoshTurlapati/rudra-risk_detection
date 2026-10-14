import React, { useEffect, useState } from 'react';
import { FileText, Download, Printer } from 'lucide-react';
import { api } from '../services/api';
import { InvestigationReport } from '../types';

const getReportFindings = (findings: unknown): unknown[] => {
  if (Array.isArray(findings)) return findings;
  if (!findings || typeof findings !== 'object') return [];
  const record = findings as Record<string, unknown>;
  if (Array.isArray(record.findings)) return record.findings;
  if (Array.isArray(record.evidence)) return record.evidence;
  if (Array.isArray(record.reasons)) return record.reasons;
  if (typeof record.summary === 'string') return [record.summary];
  return [];
};

export const Reports: React.FC = () => {
  const [reports, setReports] = useState<InvestigationReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<InvestigationReport | null>(null);
  const [error, setError] = useState('');
  const [downloadError, setDownloadError] = useState('');
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);

  const fetchReports = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getReports();
      setReports(data);
      setSelectedReport(current => (
        current ? data.find(report => report.id === current.id) || data[0] || null : data[0] || null
      ));
    } catch (err) {
      console.error('Reports could not be loaded', err);
      setError('Reports could not be loaded. Please retry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchReports();
  }, []);

  const handleDownload = async () => {
    if (!selectedReport) return;
    setDownloadError('');
    setDownloading(true);
    try {
      const blob = await api.downloadReport(selectedReport.case_number);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `RudraShield_${selectedReport.case_number}_Report.csv`;
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) {
      console.error('Report download failed', err);
      setDownloadError('Report download failed. Please try again.');
    } finally {
      setDownloading(false);
    }
  };

  const reportFindings = getReportFindings(selectedReport?.findings);

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#102447] flex items-center gap-2">
            <FileText className="w-5 h-5 text-[#087CF0]" />
            Formal Threat Intelligence Reports
          </h1>
          <p className="text-xs text-[#657792] mt-0.5">
            Exportable investigation summaries with recorded evidence, heuristic risk scores, and review recommendations
          </p>
        </div>

        {selectedReport && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.print()}
              className="px-3.5 py-2 bg-white hover:bg-gray-50 border border-[#DCE7F5] rounded-xl text-xs font-bold text-[#102447] flex items-center gap-1.5 shadow-sm"
            >
              <Printer className="w-4 h-4 text-[#087CF0]" />
              Print / Save PDF
            </button>
            <button
              onClick={handleDownload}
              disabled={downloading}
              className="px-3.5 py-2 bg-[#087CF0] hover:bg-[#076ecc] text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-colors disabled:opacity-60"
            >
              <Download className="w-4 h-4" />
              {downloading ? 'Preparing CSV...' : 'Download CSV'}
            </button>
          </div>
        )}
      </div>
      {error && (
        <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
          <span>{error}</span>
          <button type="button" onClick={fetchReports} className="font-bold underline">Retry</button>
        </div>
      )}
      {downloadError && <p role="alert" className="p-3 bg-red-50 text-red-700 rounded-xl text-xs">{downloadError}</p>}

      {loading ? (
        <div role="status" className="rounded-2xl border border-[#DCE7F5] bg-white p-8 text-center text-sm text-[#657792]">
          Loading recorded case reports...
        </div>
      ) : (
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Left Reports List */}
        <div className="lg:col-span-4 bg-white rounded-2xl border border-[#DCE7F5] shadow-card p-4 space-y-2">
          <p className="text-[11px] font-bold text-[#657792] uppercase px-2 mb-2">Available Case Reports</p>
          <div className="space-y-1.5 overflow-y-auto max-h-[600px]">
            {reports.map((rep) => (
              <button
                key={rep.id}
                onClick={() => setSelectedReport(rep)}
                className={`w-full text-left p-3 rounded-xl border transition-all text-xs ${
                  selectedReport?.id === rep.id
                    ? 'bg-[#F1F7FF] border-[#087CF0] text-[#087CF0] font-bold'
                    : 'bg-[#F8FAFC] border-transparent hover:border-[#DCE7F5] text-[#102447]'
                }`}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-mono text-[11px]">{rep.case_number}</span>
                  <span className={`px-2 py-0.2 rounded-full text-[10px] ${
                    rep.risk_score == null ? 'bg-gray-100 text-gray-700' :
                    rep.risk_score >= 80 ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'
                  }`}>
                    {rep.risk_score == null ? 'Not assessed' : `Score: ${rep.risk_score}`}
                  </span>
                </div>
                <p className="truncate font-semibold">{rep.indicator}</p>
                <p className="text-[10px] text-[#8E9EB5] mt-1">{rep.brand_name || 'No brand assigned'}</p>
              </button>
            ))}
            {reports.length === 0 && (
              <p className="py-8 text-center text-xs text-[#657792]">No case reports are recorded for this organization.</p>
            )}
          </div>
        </div>

        {/* Right Formal Report Document Preview */}
        <div className="lg:col-span-8 bg-white rounded-2xl border border-[#DCE7F5] shadow-card p-8 space-y-6 print:border-none print:shadow-none">
          {selectedReport ? (
            <div className="space-y-6">

              {/* Document Header */}
              <div className="flex justify-between items-start pb-6 border-b-2 border-[#061A3A]">
                <div>
                  <h2 className="text-xl font-black text-[#061A3A] tracking-tight">RUDRA SHIELD AI</h2>
                  <p className="text-[10px] font-semibold text-[#087CF0] uppercase tracking-widest mt-0.5">
                    DIGITAL RISK PROTECTION &bull; INCIDENT DOSSIER
                  </p>
                </div>
                <div className="text-right">
                  <p className="font-mono font-black text-sm text-[#102447]">{selectedReport.case_number}</p>
                  <p className="text-[10px] text-[#657792]">
                    Generated: {selectedReport.created_at ? new Date(selectedReport.created_at).toLocaleString() : 'Time unavailable'}
                  </p>
                </div>
              </div>

              {/* Executive Summary */}
              <div>
                <h3 className="text-xs font-bold text-[#102447] uppercase tracking-wider mb-2">
                  1. Executive Summary
                </h3>
                <p className="text-xs text-[#102447] leading-relaxed bg-[#F8FAFC] p-4 rounded-xl border border-[#E2E8F0]">
                  Stored case record for <span className="font-mono font-bold">{selectedReport.indicator}</span>.
                  Recorded disposition: <span className="font-bold">{selectedReport.status}</span>.
                  Risk score: <span className="font-bold">{selectedReport.risk_score == null ? 'not assessed' : `${selectedReport.risk_score}/100`}</span>.
                  {selectedReport.brand_name ? <> Associated registry brand: <span className="font-bold">{selectedReport.brand_name}</span>.</> : null}
                </p>
              </div>

              {/* Assessment Metrics Table */}
              <div>
                <h3 className="text-xs font-bold text-[#102447] uppercase tracking-wider mb-2">
                  2. Forensic Metrics
                </h3>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                  <div className="p-3 bg-[#F1F7FF] border border-[#B8D7FC] rounded-xl">
                    <p className="text-[10px] text-[#657792]">Target Type</p>
                    <p className="font-bold text-[#102447] mt-0.5">{selectedReport.type}</p>
                  </div>
                  <div className="p-3 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl">
                    <p className="text-[10px] text-[#657792] font-bold">Recorded Severity</p>
                    <p className="font-bold text-[#102447] mt-0.5">{selectedReport.severity || 'Not recorded'}</p>
                  </div>
                  <div className="p-3 bg-[#F1F7FF] border border-[#B8D7FC] rounded-xl">
                    <p className="text-[10px] text-[#657792]">Risk Score</p>
                    <p className="font-black text-[#102447] mt-0.5">
                      {selectedReport.risk_score == null ? 'Not assessed' : `${selectedReport.risk_score}/100`}
                    </p>
                  </div>
                  <div className="p-3 bg-[#F1F7FF] border border-[#B8D7FC] rounded-xl">
                    <p className="text-[10px] text-[#657792] font-bold">Stored Confidence (Provenance Unknown)</p>
                    <p className="font-bold text-[#102447] mt-0.5">
                      {selectedReport.confidence == null ? 'Not assessed' : `${selectedReport.confidence}%`}
                    </p>
                  </div>
                </div>
              </div>

              {/* Detection Methods & Limitations */}
              <div>
                <h3 className="text-xs font-bold text-[#102447] uppercase tracking-wider mb-2">
                  3. Methodology &amp; Limitations
                </h3>
                <p className="text-xs text-[#657792] leading-relaxed">
                  This report reflects the values and findings saved with the case. Heuristic scores are not calibrated probabilities and do not independently verify ownership or establish proof of malicious activity.
                  <span className="italic block mt-1">Review the recorded findings and independently verify evidence before taking enforcement or legal action.</span>
                </p>
              </div>

              <div>
                <h3 className="text-xs font-bold text-[#102447] uppercase tracking-wider mb-2">Recorded Findings</h3>
                {reportFindings.length > 0 ? (
                  <ul className="list-disc pl-5 space-y-1 text-xs text-[#657792]">
                    {reportFindings.map((finding, index) => (
                      <li key={index}>{typeof finding === 'string' ? finding : JSON.stringify(finding)}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-xs text-[#657792]">No findings were saved with this case.</p>
                )}
              </div>

            </div>
          ) : (
            <p className="text-xs text-[#657792]">
              {reports.length ? 'Select a report on the left to preview.' : 'No report is selected.'}
            </p>
          )}
        </div>

      </div>
      )}

    </div>
  );
};

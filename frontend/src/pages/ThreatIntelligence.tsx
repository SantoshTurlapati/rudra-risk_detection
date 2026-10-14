import React, { useEffect, useState } from 'react';
import { Brain, Search, Calendar, GitMerge } from 'lucide-react';
import { api } from '../services/api';
import { CampaignClusterSuggestion, Investigation } from '../types';

export const ThreatIntelligence: React.FC = () => {
  const [investigations, setInvestigations] = useState<Investigation[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState('all');
  const [loading, setLoading] = useState(true);
  const [clusterSuggestions, setClusterSuggestions] = useState<CampaignClusterSuggestion[]>([]);
  const [clusterLoading, setClusterLoading] = useState(true);
  const [clusterError, setClusterError] = useState('');

  useEffect(() => {
    const loadInvestigations = async () => {
      try {
        const data = await api.getInvestigations();
        setInvestigations(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    const loadClusterSuggestions = async () => {
      try {
        const result = await api.getCampaignClusterSuggestions();
        setClusterSuggestions(result.suggestions);
      } catch (err) {
        console.error(err);
        setClusterError('Evidence-based grouping suggestions could not be loaded.');
      } finally {
        setClusterLoading(false);
      }
    };
    void loadInvestigations();
    void loadClusterSuggestions();
  }, []);

  const filtered = investigations.filter(inv => {
    const matchSearch = inv.indicator.toLowerCase().includes(searchTerm.toLowerCase()) ||
                        inv.case_number.toLowerCase().includes(searchTerm.toLowerCase());
    const matchSev = selectedSeverity === 'all' || inv.severity.toLowerCase() === selectedSeverity.toLowerCase();
    return matchSearch && matchSev;
  });

  return (
    <div className="space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[#102447] flex items-center gap-2">
          <Brain className="w-5 h-5 text-[#087CF0]" />
          Threat Intelligence Feed
        </h1>
        <p className="text-xs text-[#657792] mt-0.5">
          Stored investigation catalog of recorded brand impersonation vectors, phishing indicators, and scam cases
        </p>
      </div>

      <section className="rounded-2xl border border-[#DCE7F5] bg-white p-5 shadow-card space-y-3">
        <div className="flex items-start gap-3">
          <GitMerge className="mt-0.5 h-5 w-5 text-[#087CF0]" />
          <div>
            <h2 className="text-sm font-bold text-[#102447]">Possible evidence clusters</h2>
            <p className="mt-1 text-xs text-[#657792]">
              Suggestions require at least two distinct exact evidence types shared by saved cases.
              A shared indicator alone is not treated as proof of common ownership or malicious intent.
            </p>
          </div>
        </div>
        {clusterLoading ? (
          <p role="status" className="text-xs text-[#657792]">Checking saved case evidence…</p>
        ) : clusterError ? (
          <p role="alert" className="text-xs text-red-700">{clusterError}</p>
        ) : clusterSuggestions.length === 0 ? (
          <p className="rounded-xl bg-[#F8FAFC] p-3 text-xs text-[#657792]">
            No possible clusters meet the evidence threshold in the saved cases. No external sources are queried.
          </p>
        ) : (
          <div className="space-y-3">
            {clusterSuggestions.map((suggestion, index) => (
              <div key={`${suggestion.cases[0]?.id}-${suggestion.cases[1]?.id}-${index}`} className="rounded-xl border border-[#DCE7F5] bg-[#F8FAFC] p-3">
                <p className="text-xs font-bold text-[#102447]">
                  {suggestion.cases.map(item => item.case_number).join(' · ')}
                  <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-[10px] text-amber-800">
                    Possible grouping only
                  </span>
                </p>
                <ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-[#334155]">
                  {suggestion.shared_evidence.map((evidence, evidenceIndex) => (
                    <li key={`${evidence.evidence_type}-${evidenceIndex}`}>
                      {evidence.evidence_type.replace(/_/g, ' ')}: {evidence.indicator}
                    </li>
                  ))}
                </ul>
                <p className="mt-2 text-[10px] text-[#657792]">
                  Saved evidence overlap only; analyst review required. No attribution is inferred.
                </p>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Filter and Search Bar */}
      <div className="bg-white p-4 rounded-2xl border border-[#DCE7F5] flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm">
        <div className="relative w-full sm:w-80">
          <Search className="w-4 h-4 text-[#8E9EB5] absolute left-3 top-2.5" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search indicator, domain, or case ID..."
            className="w-full pl-9 pr-4 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447] focus:outline-none focus:border-[#087CF0]"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <span className="text-xs font-bold text-[#657792]">Severity:</span>
          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="text-xs font-semibold px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-[#102447] focus:outline-none"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
      </div>

      {/* Indicators Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filtered.map((inv) => (
          <div key={inv.id} className="bg-white rounded-2xl border border-[#DCE7F5] shadow-card p-5 space-y-3 hover:shadow-card-hover transition-all">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs font-bold text-[#087CF0]">{inv.case_number}</span>
              <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-extrabold ${
                inv.severity === 'Critical' ? 'bg-red-100 text-red-700' :
                inv.severity === 'High' ? 'bg-orange-100 text-orange-700' :
                'bg-yellow-100 text-yellow-800'
              }`}>
                {inv.severity}
              </span>
            </div>

            <div>
              <p className="text-xs text-[#657792] font-semibold uppercase">{inv.type}</p>
              <h3 className="text-sm font-bold text-[#102447] font-mono mt-0.5 break-all">
                {inv.indicator}
              </h3>
            </div>

            <div className="p-2.5 bg-[#F8FAFC] rounded-xl border border-gray-100 flex items-center justify-between text-xs">
              <span className="text-[#657792]">Threat Score:</span>
              <span className="font-black text-red-600">
                {inv.risk_score == null ? 'Not assessed' : `${inv.risk_score}/100`}
              </span>
            </div>

            <div className="flex items-center justify-between text-[11px] text-[#8E9EB5] pt-1">
              <span className="flex items-center gap-1">
                <Calendar className="w-3 h-3" /> {new Date(inv.created_at).toLocaleDateString()}
              </span>
              <span className="font-semibold text-emerald-600">{inv.status}</span>
            </div>
          </div>
        ))}
      </div>

    </div>
  );
};

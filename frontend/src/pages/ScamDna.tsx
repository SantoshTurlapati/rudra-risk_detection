import React, { useState } from 'react';
import { Dna, AlertCircle, CheckCircle2, ShieldAlert, Sparkles, Filter, Tag } from 'lucide-react';
import { api } from '../services/api';
import { apiErrorMessage } from '../utils/apiErrorMessage';

export const ScamDna: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState<any>(null);
  const [error, setError] = useState('');

  const handleScan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (loading) return;
    if (!inputText.trim()) {
      setError('Enter message text to analyze.');
      setAnalysis(null);
      return;
    }
    setLoading(true);
    setError('');
    setAnalysis(null);
    try {
      const res = await api.analyzeMessage({ message_text: inputText });
      setAnalysis(res);
    } catch (err) {
      console.error('Scam DNA analysis failed', err);
      setError(apiErrorMessage(err, 'Message analysis failed. Check the input and try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">

      <div>
        <h1 className="text-xl font-bold text-[#102447] flex items-center gap-2">
          <Dna className="w-5 h-5 text-[#8B5CF6]" />
          Scam DNA Pattern Analysis
        </h1>
        <p className="text-xs text-[#657792] mt-0.5">
          Linguistic deconstruction of coercion tactics, psychological triggers, and credential harvesting signatures
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Left Input */}
        <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card space-y-4">
          <h3 className="text-sm font-bold text-[#102447]">Suspicious Threat Text</h3>
          <p className="text-xs text-[#657792]">
            Paste message, SMS, phishing email, or WhatsApp scam pitch to extract DNA signatures.
          </p>

          <form onSubmit={handleScan} className="space-y-4">
            <textarea
              rows={6}
              placeholder="Paste a message to analyze. No sample message is preloaded."
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              className="w-full p-3.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447] focus:outline-none focus:border-[#8B5CF6]"
            />

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-[#8B5CF6] to-[#087CF0] text-white font-semibold rounded-xl text-xs shadow-md shadow-purple-500/25 flex items-center justify-center gap-2 transition-all"
            >
              {loading ? 'Deconstructing Pattern...' : 'Extract Scam DNA Signatures'}
            </button>
          </form>
          {error ? (
            <p role="alert" className="rounded-lg bg-red-50 p-3 text-xs text-red-700">{error}</p>
          ) : null}

          {/* Preset Samples */}
          <div className="pt-2 border-t border-gray-100">
            <p className="text-[11px] font-bold text-[#657792] mb-2 uppercase">Synthetic Quick Test Samples:</p>
            <div className="flex flex-col gap-1.5">
              <button
                type="button"
                onClick={() => setInputText('Congratulations! You won Rs. 5000 cashback from Google Pay. Scan QR code to receive money in your bank account immediately.')}
                className="text-left text-[11px] text-[#087CF0] hover:underline truncate"
              >
                1. UPI / Cashback Prize Bait Scam
              </button>
              <button
                type="button"
                onClick={() => setInputText('Income tax refund notice: Your refund of Rs. 15,490 has been approved. Enter your net banking password & OTP to release funds.')}
                className="text-left text-[11px] text-[#087CF0] hover:underline truncate"
              >
                2. Government Scheme & OTP Harvesting
              </button>
            </div>
          </div>
        </div>

        {/* Right Findings */}
        <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-[#DCE7F5] shadow-card space-y-5">
          {analysis ? (
            <div className="space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-[#DCE7F5]">
                <div>
                  <h3 className="text-sm font-bold text-[#102447]">DNA Match Results</h3>
                  <p className="text-xs text-[#657792]">Identified deception vectors and manipulation tactics</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-bold ${
                  analysis.risk_score >= 60 ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'
                }`}>
                  {analysis.risk_score}/100 heuristic risk score
                </span>
              </div>

              {/* Matched Snippets Highlight */}
              <div>
                <h4 className="text-xs font-bold text-[#102447] uppercase mb-2">Extracted Psychological Markers</h4>
                <div className="flex flex-wrap gap-2">
                  {(analysis.details?.scam_dna?.matched_snippets || []).map((snip: string, i: number) => (
                    <span key={i} className="px-2.5 py-1 bg-red-50 text-red-700 border border-red-200 rounded-lg text-xs font-bold">
                      "{snip}"
                    </span>
                  ))}
                </div>
              </div>

              {/* Matched Categories */}
              <div>
                <h4 className="text-xs font-bold text-[#102447] uppercase mb-2">Deception Categories Triggered</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {(analysis.details?.scam_dna?.patterns_matched || []).map((pat: any, i: number) => (
                    <div key={i} className="p-3 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] text-xs">
                      <p className="font-bold text-[#8B5CF6]">{pat.category}</p>
                      <p className="text-[11px] text-[#657792] mt-0.5">{pat.description}</p>
                      <p className="text-[10px] font-extrabold text-[#087CF0] mt-1.5">Weight: +{pat.weight} pts</p>
                    </div>
                  ))}
                </div>
              </div>

              {/* Analyst Guidance */}
              <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl text-xs text-[#102447]">
                <p className="font-bold text-[#8B5CF6] mb-1">Defense Recommendation:</p>
                <p>{analysis.recommended_action}</p>
                <p className="mt-2 text-[10px] text-[#657792]">
                  Rule-based screening only; this score is not a calibrated probability or proof of malicious intent.
                </p>
              </div>
            </div>
          ) : (
            <div className="h-80 flex flex-col items-center justify-center text-center p-6 text-[#657792]">
              <Dna className="w-10 h-10 text-[#8B5CF6] mb-2" />
              <h3 className="text-sm font-bold text-[#102447]">No Scam DNA Extracted Yet</h3>
              <p className="text-xs max-w-sm mt-1">
                Enter message text on the left to extract deception vectors and signature matches.
              </p>
            </div>
          )}
        </div>

      </div>

    </div>
  );
};

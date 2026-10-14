import React, { useRef, useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  Globe, UserX, Smartphone, MessageSquare, Image as ImageIcon,
  Search, ShieldAlert, CheckCircle2, AlertTriangle, ArrowRight,
  Download, Save, FileText, ExternalLink
} from 'lucide-react';
import { api } from '../services/api';
import { BrandProfile, AnalysisResult } from '../types';
import { apiErrorMessage } from '../utils/apiErrorMessage';

export const Investigate: React.FC = () => {
  const [searchParams] = useSearchParams();
  const initialTab = searchParams.get('tab') || 'url';
  const initialQuery = searchParams.get('query') || '';

  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const [brands, setBrands] = useState<BrandProfile[]>([]);
  const [selectedBrandId, setSelectedBrandId] = useState<string>('');

  // Inputs
  const [urlInput, setUrlInput] = useState(initialQuery);
  const [handleInput, setHandleInput] = useState('');
  const [platformInput, setPlatformInput] = useState('X (Twitter)');
  const [displayNameInput, setDisplayNameInput] = useState('');
  const [profileUrlInput, setProfileUrlInput] = useState('');
  const [bioInput, setBioInput] = useState('');
  const [appNameInput, setAppNameInput] = useState('');
  const [appPackageInput, setAppPackageInput] = useState('');
  const [appDevInput, setAppDevInput] = useState('');
  const [appStoreUrlInput, setAppStoreUrlInput] = useState('');
  const [appDescriptionInput, setAppDescriptionInput] = useState('');
  const [messageInput, setMessageInput] = useState('');
  const [senderInput, setSenderInput] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // Results & State
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [savedCaseId, setSavedCaseId] = useState<string | null>(null);
  const [savingCase, setSavingCase] = useState(false);
  const savingCaseRef = useRef(false);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchBrands = async () => {
      try {
        const data = await api.getBrands();
        setBrands(data);
        if (data.length > 0) setSelectedBrandId(data[0].id);
      } catch (err) {
        setError('Unable to load the brand registry. Analysis can still run without a brand comparison.');
      }
    };
    fetchBrands();
  }, []);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (activeTab === 'url' && !urlInput.trim()) {
      setError('Enter a URL to analyze.');
      return;
    }
    if (activeTab === 'profile' && ![handleInput, displayNameInput, profileUrlInput, bioInput].some(value => value.trim())) {
      setError('Enter a handle, display name, profile URL, or profile text to analyze.');
      return;
    }
    if (activeTab === 'app' && !appNameInput.trim()) {
      setError('Enter an application name to analyze.');
      return;
    }
    if (activeTab === 'message' && !messageInput.trim()) {
      setError('Enter message text to analyze.');
      return;
    }
    if (activeTab === 'image' && !selectedFile) {
      setError('Select an image file to analyze.');
      return;
    }
    setLoading(true);
    setResult(null);
    setSavedCaseId(null);

    try {
      let res: AnalysisResult;
      if (activeTab === 'url') {
        res = await api.analyzeUrl(urlInput, selectedBrandId);
      } else if (activeTab === 'profile') {
        res = await api.analyzeProfile({
          platform: platformInput,
          handle: handleInput,
          display_name: displayNameInput || undefined,
          profile_url: profileUrlInput || undefined,
          bio_text: bioInput || undefined,
          brand_id: selectedBrandId
        });
      } else if (activeTab === 'app') {
        res = await api.analyzeApp({
          app_name: appNameInput,
          package_name: appPackageInput,
          developer_name: appDevInput,
          store_url: appStoreUrlInput || undefined,
          description: appDescriptionInput || undefined,
          brand_id: selectedBrandId
        });
      } else if (activeTab === 'message') {
        res = await api.analyzeMessage({
          message_text: messageInput,
          sender_identifier: senderInput || undefined,
          brand_id: selectedBrandId
        });
      } else {
        const formData = new FormData();
        if (selectedFile) formData.append('file', selectedFile);
        if (selectedBrandId) formData.append('brand_id', selectedBrandId);
        res = await api.analyzeImage(formData);
      }
      setResult(res);
    } catch (err) {
      setError(apiErrorMessage(err, 'Analysis failed. Check the input and try again.'));
    } finally {
      setLoading(false);
    }
  };

  const handleSaveInvestigation = async () => {
    if (!result || savingCaseRef.current || savedCaseId) return;
    savingCaseRef.current = true;
    setSavingCase(true);
    setError('');
    try {
      const saved = await api.createInvestigation({
        indicator: result.indicator,
        type: result.type,
        risk_score: result.risk_score,
        confidence: result.confidence,
        status: result.status,
        severity: result.risk_score == null ? 'Not assessed' :
          result.risk_score >= 75 ? 'Critical' : result.risk_score >= 50 ? 'High' : 'Medium',
        findings: result,
        brand_id: selectedBrandId,
        analyst_notes: `Candidate investigated via ${activeTab} modality. Threat band: ${result.risk_band}.`
      });
      setSavedCaseId(saved.case_number);
    } catch (err) {
      setError(apiErrorMessage(err, 'The analysis could not be saved. Please try again.'));
    } finally {
      savingCaseRef.current = false;
      setSavingCase(false);
    }
  };

  return (
    <div className="space-y-6">

      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-[#102447]">Multimodal Investigation Center</h1>
        <p className="text-xs text-[#657792] mt-0.5">
          Explainable rule-based review of URLs, pasted profiles, apps, messages, and uploaded images
        </p>
      </div>
      {error && <p role="alert" className="p-3 bg-red-50 text-red-700 rounded-xl text-xs">{error}</p>}

      {/* Target Brand Selector */}
      <div className="bg-white p-4 rounded-2xl border border-[#DCE7F5] flex flex-col sm:flex-row items-center justify-between gap-4 shadow-sm">
        <div className="flex items-center gap-2">
          <label htmlFor="brand-select" className="text-xs font-semibold text-[#102447]">Compare with brand:</label>
          <select
            id="brand-select"
            value={selectedBrandId}
            onChange={(e) => setSelectedBrandId(e.target.value)}
            className="text-xs font-bold text-[#087CF0] bg-[#F1F7FF] border border-[#B8D7FC] rounded-lg px-3 py-1.5 focus:outline-none"
          >
            {brands.map((b) => (
              <option key={b.id} value={b.id}>{b.name}{b.is_verified ? '' : ' (unverified)'}</option>
            ))}
          </select>
        </div>

        <div className="text-[11px] text-[#657792]">
          Registry comparisons use verified records only. No social platform, app store, or live threat feed is queried.
        </div>
      </div>

      {/* Main Analysis Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Left Form (Tabs) */}
        <div className="lg:col-span-5 bg-white p-5 rounded-2xl border border-[#DCE7F5] shadow-card space-y-5">

          {/* Tab Selector */}
          <div className="grid grid-cols-5 gap-1 p-1 bg-[#F1F7FF] rounded-xl border border-[#DCE7F5]">
            {[
              { id: 'url', label: 'URL', icon: Globe },
              { id: 'profile', label: 'Profile', icon: UserX },
              { id: 'app', label: 'App', icon: Smartphone },
              { id: 'message', label: 'Message', icon: MessageSquare },
              { id: 'image', label: 'Image', icon: ImageIcon },
            ].map((tab) => {
              const Icon = tab.icon;
              return (
                <button
                  key={tab.id}
                  type="button"
                  aria-pressed={activeTab === tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-2 flex flex-col items-center justify-center gap-1 rounded-lg text-[10px] font-bold transition-all ${
                    activeTab === tab.id
                      ? 'bg-white text-[#087CF0] shadow-sm'
                      : 'text-[#657792] hover:text-[#102447]'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>

          <form onSubmit={handleAnalyze} className="space-y-4">
            {/* Tab: URL */}
            {activeTab === 'url' && (
              <div className="space-y-3">
                <label className="text-xs font-bold text-[#102447]">Target Website / Link</label>
                <input
                  type="text"
                  value={urlInput}
                  onChange={(e) => setUrlInput(e.target.value)}
                  placeholder="https://sbi-verify-kyc-login.xyz/update"
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447] focus:outline-none focus:border-[#087CF0]"
                />
                <p className="text-[10px] text-[#657792]">
                  Checks SSRF risks, Punycode deception, domain typosquatting, and brand path mimicry.
                </p>
              </div>
            )}

            {/* Tab: Profile */}
            {activeTab === 'profile' && (
              <div className="space-y-3">
                <label className="text-xs font-bold text-[#102447]" htmlFor="profile-platform">Social media platform</label>
                <select
                  id="profile-platform"
                  value={platformInput}
                  onChange={(e) => setPlatformInput(e.target.value)}
                  className="w-full px-3.5 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447]"
                >
                  <option>X (Twitter)</option>
                  <option>Instagram</option>
                  <option>Facebook</option>
                  <option>Telegram</option>
                  <option>WhatsApp</option>
                </select>

                <label className="text-xs font-bold text-[#102447]" htmlFor="profile-handle">Handle / Account ID (optional)</label>
                <input
                  id="profile-handle"
                  type="text"
                  value={handleInput}
                  onChange={(e) => setHandleInput(e.target.value)}
                  placeholder="@account_handle"
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447] focus:outline-none focus:border-[#087CF0]"
                />
                <label className="text-xs font-bold text-[#102447]" htmlFor="profile-display-name">Displayed account name (optional)</label>
                <input
                  id="profile-display-name"
                  type="text"
                  value={displayNameInput}
                  onChange={(e) => setDisplayNameInput(e.target.value)}
                  maxLength={255}
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447] focus:outline-none focus:border-[#087CF0]"
                />
                <label className="text-xs font-bold text-[#102447]" htmlFor="profile-url">Profile URL (optional)</label>
                <input
                  id="profile-url"
                  type="url"
                  value={profileUrlInput}
                  onChange={(e) => setProfileUrlInput(e.target.value)}
                  maxLength={2048}
                  placeholder="https://example.com/profile"
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447] focus:outline-none focus:border-[#087CF0]"
                />
                <label className="text-xs font-bold text-[#102447]" htmlFor="profile-bio">Bio or profile text (optional)</label>
                <textarea
                  id="profile-bio"
                  rows={3}
                  value={bioInput}
                  onChange={(e) => setBioInput(e.target.value)}
                  maxLength={5000}
                  placeholder="Paste only profile details you are authorized to analyze."
                  className="w-full p-3 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447] focus:outline-none focus:border-[#087CF0]"
                />
                <p className="text-[10px] text-[#657792]">
                  Account age, follower counts, verification badges, and ownership are not retrieved or inferred.
                </p>
              </div>
            )}

            {/* Tab: App */}
            {activeTab === 'app' && (
              <div className="space-y-3">
                <label className="text-xs font-bold text-[#102447]">Application Name</label>
                <input
                  type="text"
                  value={appNameInput}
                  onChange={(e) => setAppNameInput(e.target.value)}
                  placeholder="QuickReward UPI"
                  className="w-full px-3.5 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447]"
                />
                <label className="text-xs font-bold text-[#102447]">Package ID</label>
                <input
                  type="text"
                  value={appPackageInput}
                  onChange={(e) => setAppPackageInput(e.target.value)}
                  placeholder="com.upi.reward.fake"
                  className="w-full px-3.5 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447]"
                />
                <label className="text-xs font-bold text-[#102447]">Publisher / Developer</label>
                <input
                  type="text"
                  value={appDevInput}
                  onChange={(e) => setAppDevInput(e.target.value)}
                  placeholder="Quick Tech Apps Ltd"
                  className="w-full px-3.5 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447]"
                />
                <label className="text-xs font-bold text-[#102447]" htmlFor="app-store-url">
                  Submitted app-store URL (optional)
                </label>
                <input
                  id="app-store-url"
                  type="url"
                  value={appStoreUrlInput}
                  onChange={(e) => setAppStoreUrlInput(e.target.value)}
                  maxLength={2048}
                  placeholder="https://store.example/apps/candidate"
                  className="w-full px-3.5 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447]"
                />
                <p className="text-[10px] text-[#657792]">
                  URL structure is screened locally. No store listing or signature is retrieved.
                </p>
                <label className="text-xs font-bold text-[#102447]" htmlFor="app-description">
                  App description (optional)
                </label>
                <textarea
                  id="app-description"
                  rows={3}
                  value={appDescriptionInput}
                  onChange={(e) => setAppDescriptionInput(e.target.value)}
                  maxLength={5000}
                  className="w-full p-3 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447]"
                />
              </div>
            )}

            {/* Tab: Message */}
            {activeTab === 'message' && (
              <div className="space-y-3">
                <label className="text-xs font-bold text-[#102447]" htmlFor="message-text">Message text (SMS, chat, email, etc.)</label>
                <textarea
                  id="message-text"
                  rows={4}
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  maxLength={10000}
                  placeholder="Paste message contents here..."
                  className="w-full p-3 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447] focus:outline-none focus:border-[#087CF0]"
                />
                <label className="text-xs font-bold text-[#102447]" htmlFor="message-sender">Sender identifier (optional)</label>
                <input
                  id="message-sender"
                  type="text"
                  value={senderInput}
                  onChange={(e) => setSenderInput(e.target.value)}
                  maxLength={255}
                  className="w-full px-3.5 py-2.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447] focus:outline-none focus:border-[#087CF0]"
                />
              </div>
            )}

            {/* Tab: Image */}
            {activeTab === 'image' && (
              <div className="space-y-3">
                <label className="text-xs font-bold text-[#102447]">Upload Screenshot or Logo Asset</label>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  className="w-full text-xs text-[#657792] file:mr-4 file:py-2 file:px-4 file:rounded-xl file:border-0 file:text-xs file:font-semibold file:bg-[#087CF0] file:text-white hover:file:bg-[#076ecc]"
                />
                <p className="text-[10px] text-[#657792]">
                  Compares against active saved references for the selected brand when the reference schema and private storage are configured. Similarity is heuristic and does not prove impersonation.
                </p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-[#087CF0] to-[#06C8F9] hover:from-[#076ecc] hover:to-[#05b8e5] text-white font-semibold rounded-xl text-xs shadow-md shadow-blue-500/25 flex items-center justify-center gap-2 transition-all"
            >
              {loading ? (
                <span>Executing Detection Pipeline...</span>
              ) : (
                <>
                  <Search className="w-4 h-4" />
                  <span>Run Multimodal Threat Analysis</span>
                </>
              )}
            </button>
          </form>

        </div>

        {/* Right Output Panel */}
        <div className="lg:col-span-7 bg-white p-6 rounded-2xl border border-[#DCE7F5] shadow-card space-y-5">
          {result ? (
            <div className="space-y-5">

              {/* Header result row */}
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-4 border-b border-[#DCE7F5]">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold uppercase text-[#657792]">Analyzed Indicator</span>
                    <span className={`px-2.5 py-0.5 rounded-full text-xs font-extrabold ${
                      result.risk_score == null
  ? 'bg-gray-100 text-gray-700'
  : /critical|malicious/i.test(`${result.risk_band} ${result.status}`)
    ? 'bg-red-100 text-red-700'
    : /high|suspicious/i.test(`${result.risk_band} ${result.status}`)
      ? 'bg-orange-100 text-orange-700'
      : /review/i.test(result.risk_band)
        ? 'bg-amber-100 text-amber-800'
        : 'bg-slate-100 text-slate-700'
                    }`}>
                      {result.risk_band}
                    </span>
                  </div>
                  <p className="text-base font-bold text-[#102447] font-mono mt-0.5 break-all">
                    {result.indicator}
                  </p>
                </div>

                {/* Score Pill */}
                <div className="flex items-center gap-3 bg-[#F1F7FF] px-4 py-2 rounded-xl border border-[#B8D7FC]">
                  <div className="text-right">
                    <p className="text-[10px] font-bold text-[#657792] uppercase">Heuristic Risk Score</p>
                    <p className="text-xs font-semibold text-[#087CF0]">
                      Confidence estimate: {result.confidence == null ? 'Not available' : `${result.confidence}%`}
                    </p>
                  </div>
                  <div className={`text-3xl font-black ${
                    result.risk_score == null
  ? 'text-gray-500'
  : /critical|malicious/i.test(`${result.risk_band} ${result.status}`)
    ? 'text-red-600'
    : /high|suspicious/i.test(`${result.risk_band} ${result.status}`)
      ? 'text-orange-500'
      : /review/i.test(result.risk_band)
        ? 'text-amber-600'
        : 'text-slate-700'
                  }`}>
                    {result.risk_score ?? '—'}
                  </div>

{/* URL-Specific Risk Score */}
{
  result.details?.url_metrics?.risk_score != null && (
  <div className="flex items-center gap-3 bg-amber-50 px-4 py-2 rounded-xl border border-amber-200">
    <div className="text-right">
      <p className="text-[10px] font-bold text-amber-800 uppercase">
        URL Risk Score
      </p>
      <p className="text-xs font-medium text-amber-700">
        Heuristic indicators
      </p>
    </div>
    <div className="text-3xl font-black text-amber-700">
      {result.details.url_metrics.risk_score}
      <span className="text-sm font-semibold">/100</span>
    </div>
  </div>
)}


                </div>
              </div>

              <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
                <p className="text-xs font-bold text-[#102447]">What this means</p>
                <p className="mt-1 text-xs text-[#334155]">
                  {result.explanations?.plain_language || 'Automated indicators are for review and do not prove fraud.'}
                </p>
                <p className="mt-2 text-[10px] font-semibold text-[#657792]">
                  Analysis source: {result.model_source || 'rules'} · heuristic score, not a probability. Human review is required.
                </p>
              </div>

              {result.type === 'image' && result.details?.comparison && (
                <div className="rounded-xl border border-[#DCE7F5] bg-white p-4">
                  <p className="text-xs font-bold text-[#102447]">Image reference comparison</p>
                  {result.details.comparison.comparison_available ? (
                    <>
                      <p className="mt-1 text-xs text-[#334155]">
                        Compared with {result.details.comparison.references_compared} active organization-submitted reference(s).
                        Review threshold: {result.details.comparison.review_threshold}%.
                      </p>
                      <ul className="mt-2 space-y-2">
                        {result.details.comparison.matches.map((match: {
                          reference_id: string;
                          similarity_score: number;
                          review_recommended: boolean;
                          interpretation: string;
                        }) => (
                          <li key={match.reference_id} className="rounded-lg bg-[#F8FAFC] p-2 text-xs">
                            <span className="font-semibold text-[#102447]">
                              Similarity score: {match.similarity_score}%
                            </span>
                            <span className="ml-2 text-[#657792]">
                              {match.review_recommended ? 'Review recommended' : 'Below review threshold'}
                            </span>
                            <p className="mt-1 text-[#657792]">{match.interpretation}</p>
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : (
                    <p className="mt-1 text-xs text-[#657792]">
                      {result.findings[0] || 'No active saved reference is available; image comparison was not performed.'}
                    </p>
                  )}
                  <p className="mt-2 text-[10px] text-[#657792]">
                    Similarity is a perceptual-hash heuristic; it is not proof of impersonation or authenticity.
                  </p>
                </div>
              )}

              {/* Signals breakdown */}
              {(result.signals.length > 0 || result.explanations?.technical) && (
                <details className="rounded-xl border border-[#DCE7F5] p-3">
                  <summary className="cursor-pointer text-xs font-bold text-[#102447]">
                    Technical evidence and score contributions
                  </summary>
                  {result.explanations?.technical && (
                    <p className="mt-2 text-xs text-[#657792]">{result.explanations.technical}</p>
                  )}
                  <div className="mt-2 space-y-2">
                    {result.signals.map((sig, idx) => (
                      <div key={idx} className="p-3 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0] flex items-center justify-between text-xs">
                        <div>
                          <span className="font-bold text-[#102447]">{sig.source}:</span>{' '}
                          <span className="text-[#657792]">{sig.detail}</span>
                        </div>
                        <span className="font-extrabold text-[#087CF0] ml-2">+{sig.contribution} pts</span>
                      </div>
                    ))}
                  </div>
                  {(result.details?.scam_dna?.evidence?.length > 0 ||
                    result.details?.urls?.length > 0) && (
                    <div className="mt-3 space-y-2 border-t border-[#DCE7F5] pt-3">
                      {result.details?.scam_dna?.evidence?.map((item: any, index: number) => (
                        <p key={`text-${index}`} className="text-xs text-[#334155]">
                          <strong>{item.category}:</strong> “{item.excerpt}” — {item.explanation}
                        </p>
                      ))}
                      {result.details?.urls?.map((item: any, index: number) => (
                        <p key={`url-${index}`} className="break-all text-xs text-[#334155]">
                          <strong>URL indicator:</strong> {item.url} · {item.risk_score == null
                            ? item.error || 'Not parsed'
                            : `local structure score ${item.risk_score}/100`}
                        </p>
                      ))}
                    </div>
                  )}
                </details>
              )}

              {/* Matched Findings */}
              <div>
                <h4 className="text-xs font-bold text-[#102447] uppercase tracking-wider mb-2">
                  Key Evidence Findings
                </h4>
                <ul className="space-y-1.5 text-xs text-[#102447]">
                  {result.findings.map((f, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Recommended Action */}
              <div className="p-3.5 bg-blue-50 border border-blue-200 rounded-xl">
                <p className="text-[11px] font-bold text-[#087CF0] uppercase tracking-wider">
                  Recommended Analyst Action
                </p>
                <p className="text-xs font-medium text-[#102447] mt-0.5">
                  {result.recommended_action}
                </p>
              </div>

              {(result.missing_information.length > 0 || (result.limitations?.length ?? 0) > 0) && (
                <div className="rounded-xl border border-amber-200 bg-amber-50 p-3.5">
                  <p className="text-[11px] font-bold uppercase tracking-wider text-amber-800">Missing data and limitations</p>
                  <ul className="mt-1 list-disc space-y-1 pl-4 text-xs text-[#334155]">
                    {[...result.missing_information, ...(result.limitations || [])].map((item, index) => (
                      <li key={index}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Action Buttons */}
              <div className="pt-2 flex flex-wrap items-center gap-3">
                <button
                  onClick={handleSaveInvestigation}
                  type="button"
                  disabled={savingCase || savedCaseId !== null}
                  aria-busy={savingCase}
                  className="px-4 py-2 bg-[#087CF0] hover:bg-[#076ecc] disabled:opacity-60 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm transition-colors"
                >
                  <Save className="w-3.5 h-3.5" />
                  {savingCase
                    ? 'Saving case…'
                    : savedCaseId
                      ? `Saved as Case #${savedCaseId}`
                      : 'Save to Case Registry'}
                </button>
              </div>

            </div>
          ) : (
            <div className="h-80 flex flex-col items-center justify-center text-center p-6 text-[#657792]">
              <div className="w-16 h-16 rounded-2xl bg-[#F1F7FF] flex items-center justify-center mb-3">
                <Search className="w-8 h-8 text-[#087CF0]" />
              </div>
              <h3 className="text-sm font-bold text-[#102447]">Awaiting Analysis Target</h3>
              <p className="text-xs max-w-sm mt-1 leading-relaxed">
                Choose a mode and provide evidence to receive a bounded, rule-based assessment. URLs are analyzed locally and never fetched.
              </p>
            </div>
          )}
        </div>

      </div>

    </div>
  );
};

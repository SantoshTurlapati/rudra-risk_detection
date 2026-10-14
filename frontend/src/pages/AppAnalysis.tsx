import React, { useEffect, useState } from 'react';
import { Smartphone, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import { AnalysisResult, BrandProfile } from '../types';
import { apiErrorMessage } from '../utils/apiErrorMessage';

export const AppAnalysis: React.FC = () => {
  const [brands, setBrands] = useState<BrandProfile[]>([]);
  const [selectedBrandId, setSelectedBrandId] = useState('');
  const [appName, setAppName] = useState('');
  const [packageName, setPackageName] = useState('');
  const [developerName, setDeveloperName] = useState('');
  const [storeUrl, setStoreUrl] = useState('');
  const [description, setDescription] = useState('');
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [brandsLoading, setBrandsLoading] = useState(true);
  const [brandLoadError, setBrandLoadError] = useState('');
  const [error, setError] = useState('');

  const loadBrands = async () => {
    setBrandsLoading(true);
    setBrandLoadError('');
    try {
      setBrands(await api.getBrands());
    } catch (err) {
      console.error('Failed to load brands', err);
      setBrandLoadError(apiErrorMessage(err, 'Brand registry could not be loaded.'));
    } finally {
      setBrandsLoading(false);
    }
  };

  useEffect(() => {
    void loadBrands();
  }, []);

  const selectedBrand = brands.find((brand) => brand.id === selectedBrandId);
  const registeredApps = selectedBrand?.official_apps || [];

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setAnalysisResult(null);
    try {
      const result = await api.analyzeApp({
        app_name: appName,
        package_name: packageName || undefined,
        developer_name: developerName || undefined,
        store_url: storeUrl || undefined,
        description: description || undefined,
        brand_id: selectedBrandId || undefined,
      });
      setAnalysisResult(result);
    } catch (err) {
      console.error('App analysis failed', err);
      setError(apiErrorMessage(err, 'App analysis failed. Check the input and try again.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold text-[#102447] flex items-center gap-2">
          <Smartphone className="w-5 h-5 text-[#8B5CF6]" />
          Mobile Application Impersonation Inspector
        </h1>
        <p className="text-xs text-[#657792] mt-0.5">
          Compare submitted app details with the selected organization registry and heuristic checks.
          No app-store lookup or publisher-signature verification is configured.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white rounded-2xl border border-[#DCE7F5] shadow-card p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-gray-100">
            <h2 className="text-sm font-bold text-[#102447]">Configured App Registry</h2>
            <span className={`px-2 py-0.5 text-[10px] font-bold rounded-md ${
              selectedBrand?.is_verified
                ? 'bg-emerald-50 text-emerald-700'
                : 'bg-amber-50 text-amber-700'
            }`}>
              {selectedBrand ? (selectedBrand.is_verified ? 'Admin-marked verified' : 'Unverified') : 'No brand selected'}
            </span>
          </div>

          {brandsLoading ? (
            <p className="text-xs text-[#657792]" role="status">Loading organization brands…</p>
          ) : null}
          {brandLoadError ? (
            <div role="alert" className="flex items-center justify-between gap-2 rounded-lg bg-red-50 p-2 text-xs text-red-700">
              <span>{brandLoadError}</span>
              <button type="button" onClick={() => void loadBrands()} className="font-bold underline">Retry</button>
            </div>
          ) : null}
          <label className="block text-[11px] font-bold text-[#102447]">
            Organization brand
            <select
              value={selectedBrandId}
              onChange={(e) => setSelectedBrandId(e.target.value)}
              disabled={brandsLoading || brands.length === 0}
              className="mt-1 w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
            >
              <option value="">Select a brand</option>
              {brands.map((brand) => (
                <option key={brand.id} value={brand.id}>{brand.name}</option>
              ))}
            </select>
          </label>

          {registeredApps.length > 0 ? (
            <ul className="space-y-3">
              {registeredApps.map((app, index) => (
                <li key={`${app.package_id}-${index}`} className="p-3 bg-[#F8FAFC] rounded-xl border border-[#E2E8F0]">
                  <p className="font-bold text-xs text-[#102447]">{app.name || 'Unnamed registry entry'}</p>
                  <p className="font-mono text-[11px] text-[#087CF0] mt-1">{app.package_id || 'Package ID not recorded'}</p>
                  <p className="text-[11px] text-[#657792] mt-1">
                    Publisher: {app.developer || 'Not recorded'}
                  </p>
                </li>
              ))}
            </ul>
          ) : (
            <p className="py-6 text-center text-xs text-[#657792]">
              {brandsLoading
                ? 'Loading registered app metadata.'
                : selectedBrand
                  ? 'No official app references are recorded for this brand.'
                  : brands.length === 0
                    ? 'No brand records are available for this organization.'
                    : 'Select a brand to view its stored app references.'}
            </p>
          )}
        </div>

        <div className="bg-white rounded-2xl border border-[#DCE7F5] shadow-card p-6 space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-gray-100">
            <AlertTriangle className="w-4 h-4 text-amber-600" />
            <h2 className="text-sm font-bold text-[#102447]">Candidate App Details</h2>
          </div>
          <form onSubmit={handleAnalyze} className="space-y-3">
            <label className="block text-[11px] font-bold text-[#102447]">
              App name
              <input
                required
                value={appName}
                onChange={(e) => setAppName(e.target.value)}
                className="mt-1 w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
              />
            </label>
            <label className="block text-[11px] font-bold text-[#102447]">
              Package identifier
              <input
                value={packageName}
                onChange={(e) => setPackageName(e.target.value)}
                className="mt-1 w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs font-mono"
              />
            </label>
            <label className="block text-[11px] font-bold text-[#102447]">
              Claimed developer / publisher
              <input
                value={developerName}
                onChange={(e) => setDeveloperName(e.target.value)}
                className="mt-1 w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
              />
            </label>
            <label className="block text-[11px] font-bold text-[#102447]">
              Submitted app-store URL (optional)
              <input
                type="url"
                value={storeUrl}
                onChange={(e) => setStoreUrl(e.target.value)}
                placeholder="https://store.example/apps/example"
                className="mt-1 w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
              />
              <span className="mt-1 block font-normal text-[#657792]">
                Checked locally for URL indicators only; no app store is queried.
              </span>
            </label>
            <label className="block text-[11px] font-bold text-[#102447]">
              Description
              <textarea
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="mt-1 w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
              />
            </label>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 bg-[#087CF0] hover:bg-[#076ecc] disabled:opacity-60 text-white rounded-xl text-xs font-bold shadow-md"
            >
              {loading ? 'Evaluating...' : 'Run Heuristic Analysis'}
            </button>
          </form>
        </div>
      </div>

      {error && <p role="alert" className="p-3 bg-red-50 text-red-700 rounded-xl text-xs">{error}</p>}

      {analysisResult && (
        <div className="bg-white rounded-2xl border border-[#DCE7F5] shadow-card p-6 space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 pb-3 border-b border-[#DCE7F5]">
            <div>
              <h2 className="text-sm font-bold text-[#102447]">Heuristic Analysis Results</h2>
              <p className="text-xs text-[#657792] mt-1">{analysisResult.indicator}</p>
            </div>
            <span className="px-3 py-1 rounded-full bg-amber-50 text-amber-800 text-xs font-bold">
              {analysisResult.risk_score == null
                ? 'Risk not assessed'
                : `${analysisResult.risk_score}/100 · ${analysisResult.risk_band}`}
            </span>
          </div>
          <p className="text-xs text-[#657792]">
            Confidence estimate: {analysisResult.confidence == null ? 'Not available' : `${analysisResult.confidence}%`}
          </p>
          <div>
            <h3 className="text-xs font-bold text-[#102447] uppercase mb-2">Findings</h3>
            <ul className="list-disc pl-5 space-y-1 text-xs text-[#657792]">
              {analysisResult.findings.map((finding, index) => <li key={index}>{finding}</li>)}
            </ul>
          </div>
          {analysisResult.signals.length > 0 && (
            <div>
              <h3 className="text-xs font-bold text-[#102447] uppercase mb-2">Signals</h3>
              <ul className="space-y-2">
                {analysisResult.signals.map((signal, index) => (
                  <li key={index} className="p-3 bg-[#F8FAFC] rounded-xl text-xs">
                    <strong>{signal.source} ({signal.contribution} pts):</strong> {signal.detail}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {analysisResult.details?.submitted_store_url_analysis && (
            <div className="rounded-xl border border-[#DCE7F5] bg-[#F8FAFC] p-3">
              <h3 className="text-xs font-bold text-[#102447] uppercase mb-1">
                Submitted app-store URL · local screening only
              </h3>
              <p className="break-all font-mono text-[11px] text-[#657792]">
                {analysisResult.details.submitted_store_url_analysis.url}
              </p>
              <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-[#657792]">
                {analysisResult.details.submitted_store_url_analysis.reasons.map(
                  (reason: string, index: number) => <li key={index}>{reason}</li>
                )}
              </ul>
              <p className="mt-2 text-[10px] text-[#657792]">
                No listing was fetched; URL indicators do not verify the app or publisher.
              </p>
            </div>
          )}
          {analysisResult.missing_information.length > 0 && (
            <div>
              <h3 className="text-xs font-bold text-[#102447] uppercase mb-2">Limitations</h3>
              <ul className="list-disc pl-5 space-y-1 text-xs text-[#657792]">
                {analysisResult.missing_information.map((item, index) => <li key={index}>{item}</li>)}
              </ul>
            </div>
          )}
          <p className="text-xs text-[#102447]"><strong>Recommended next step:</strong> {analysisResult.recommended_action}</p>
        </div>
      )}
    </div>
  );
};

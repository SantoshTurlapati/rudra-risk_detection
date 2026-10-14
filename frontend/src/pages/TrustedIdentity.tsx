import React, { useEffect, useState } from 'react';
import {
  ShieldCheck, Plus, Globe, Smartphone, UserX,
  Trash2, Edit, CheckCircle2, Building2, Phone, Mail, X
} from 'lucide-react';
import { api } from '../services/api';
import { BrandImageReference, BrandProfile } from '../types';
import { apiErrorMessage } from '../utils/apiErrorMessage';

const BrandImageReferences: React.FC<{ brand: BrandProfile }> = ({ brand }) => {
  const [references, setReferences] = useState<BrandImageReference[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState('');

  const loadReferences = async () => {
    setLoading(true);
    setError('');
    try {
      setReferences(await api.getBrandImageReferences(brand.id));
    } catch (err) {
      console.error('Failed to load official image references', err);
      setError(apiErrorMessage(
        err,
        'Official image references are unavailable. Check migration and private-storage configuration, then retry.'
      ));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadReferences();
  }, [brand.id]);

  const upload = async (file: File, referenceId?: string) => {
    setWorking(true);
    setError('');
    try {
      if (referenceId) {
        await api.replaceBrandImageReference(brand.id, referenceId, file);
      } else {
        await api.uploadBrandImageReference(brand.id, file);
      }
      await loadReferences();
    } catch (err) {
      console.error('Failed to save official image reference', err);
      try {
        setReferences(await api.getBrandImageReferences(brand.id));
      } catch (refreshError) {
        console.error('Failed to refresh image references after a save error', refreshError);
      }
      setError(apiErrorMessage(
        err,
        'Image reference could not be saved. Check your administrator access and storage configuration.'
      ));
    } finally {
      setWorking(false);
    }
  };

  const remove = async (referenceId: string) => {
    setWorking(true);
    setError('');
    try {
      await api.removeBrandImageReference(brand.id, referenceId);
      await loadReferences();
    } catch (err) {
      console.error('Failed to remove official image reference', err);
      try {
        setReferences(await api.getBrandImageReferences(brand.id));
      } catch (refreshError) {
        console.error('Failed to refresh image references after a removal error', refreshError);
      }
      setError(apiErrorMessage(err, 'Image reference could not be removed. Please retry.'));
    } finally {
      setWorking(false);
    }
  };

  return (
    <section className="space-y-2 border-t border-gray-100 pt-3" aria-label={`${brand.name} image references`}>
      <div className="flex items-center justify-between gap-2">
        <div>
          <h4 className="text-[10px] font-bold uppercase text-[#657792]">Private image references</h4>
          <p className="text-[10px] text-[#657792]">Organization-submitted assets; not independently verified.</p>
        </div>
        <label className="cursor-pointer rounded-lg border border-[#D0E4FA] px-2 py-1 text-[10px] font-bold text-[#087CF0] hover:bg-[#F1F7FF]">
          Add image
          <input
            aria-label={`Add image reference for ${brand.name}`}
            className="sr-only"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            disabled={working}
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) void upload(file);
              event.currentTarget.value = '';
            }}
          />
        </label>
      </div>
      {loading ? <p className="text-[11px] text-[#657792]">Loading image references…</p> : null}
      {error ? (
        <div role="alert" className="flex items-center justify-between gap-2 rounded-lg bg-amber-50 p-2 text-[11px] text-amber-800">
          <span>{error}</span>
          <button type="button" onClick={() => void loadReferences()} className="font-bold underline">Retry</button>
        </div>
      ) : null}
      {!loading && !error && references.length === 0 ? (
        <p className="text-[11px] text-[#657792]">No saved image references. Image comparison is unavailable.</p>
      ) : null}
      {references.map((reference) => (
        <div key={reference.id} className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-[#F8FAFC] p-2 text-[10px]">
          <span className="font-mono text-[#657792]">
            {reference.status === 'active' ? 'Active · ' : 'Removed · '}
            {reference.media_type} · {Math.ceil(reference.size_bytes / 1024)} KB · SHA-256 {reference.content_hash.slice(0, 12)}…
          </span>
          <div className="flex gap-2">
            {reference.status === 'active' ? <label className="cursor-pointer font-bold text-[#087CF0] underline">
              Replace
              <input
                aria-label={`Replace image reference for ${brand.name}`}
                className="sr-only"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                disabled={working}
                onChange={(event) => {
                  const file = event.currentTarget.files?.[0];
                  if (file) void upload(file, reference.id);
                  event.currentTarget.value = '';
                }}
              />
            </label> : null}
            <button
              type="button"
              disabled={working}
              onClick={() => void remove(reference.id)}
              className="font-bold text-red-600 underline disabled:opacity-50"
            >
              Remove
            </button>
          </div>
        </div>
      ))}
    </section>
  );
};

export const TrustedIdentity: React.FC = () => {
  const [brands, setBrands] = useState<BrandProfile[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [deletingBrandId, setDeletingBrandId] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingBrand, setEditingBrand] = useState<BrandProfile | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [legalName, setLegalName] = useState('');
  const [description, setDescription] = useState('');
  const [domainsInput, setDomainsInput] = useState('');
  const [socialsInput, setSocialsInput] = useState('');
  const [appsInput, setAppsInput] = useState('');
  const [publishersInput, setPublishersInput] = useState('');
  const [contactsInput, setContactsInput] = useState('');

  const fetchBrands = async () => {
    setLoading(true);
    setErrorMessage('');
    try {
      const data = await api.getBrands();
      setBrands(data);
    } catch (err) {
      console.error("Failed to load brands", err);
      setErrorMessage(apiErrorMessage(err, 'Brand registry could not be loaded. Please retry.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBrands();
  }, []);

  const openCreateModal = () => {
    setEditingBrand(null);
    setName('');
    setLegalName('');
    setDescription('');
    setDomainsInput('');
    setSocialsInput('');
    setAppsInput('');
    setPublishersInput('');
    setContactsInput('');
    setModalOpen(true);
  };

  const openEditModal = (b: BrandProfile) => {
    setEditingBrand(b);
    setName(b.name);
    setLegalName(b.legal_name || '');
    setDescription(b.description || '');
    setDomainsInput(b.official_domains.join(', '));
    setSocialsInput(b.official_socials.map(s => `${s.platform}:${s.handle}`).join(', '));
    setAppsInput(b.official_apps.map(a => `${a.name}:${a.package_id || ''}`).join(', '));
    setPublishersInput(b.authorized_publishers.join(', '));
    setContactsInput(b.contact_identifiers.join(', '));
    setModalOpen(true);
  };

  const handleSaveBrand = async (e: React.FormEvent) => {
    e.preventDefault();
    const domains = domainsInput.split(',').map(d => d.trim()).filter(Boolean);
    const publishers = publishersInput.split(',').map(p => p.trim()).filter(Boolean);
    const contacts = contactsInput.split(',').map(c => c.trim()).filter(Boolean);

    const socials = socialsInput.split(',').map(s => {
      const parts = s.split(':');
      const platform = parts[0]?.trim() || '';
      const handle = parts[1]?.trim() || '';
      const existing = editingBrand?.official_socials.find(
        item => item.platform === platform && item.handle === handle
      );
      return { ...existing, platform, handle, url: existing?.url || '' };
    }).filter(s => s.platform && s.handle);

    const apps = appsInput.split(',').map(a => {
      const parts = a.split(':');
      const name = parts[0]?.trim() || a.trim();
      const existing = editingBrand?.official_apps.find(item => item.name === name)
        || (parts[1]?.trim()
          ? editingBrand?.official_apps.find(item => item.package_id === parts[1].trim())
          : undefined);
      return {
        ...existing,
        name,
        package_id: parts[1]?.trim() || existing?.package_id || '',
      };
    }).filter(a => a.name);

    setErrorMessage('');
    setSaving(true);
    try {
      if (editingBrand) {
        await api.updateBrand(editingBrand.id, {
          name,
          legal_name: legalName,
          description,
          official_domains: domains,
          official_socials: socials,
          official_apps: apps,
          authorized_publishers: publishers,
          contact_identifiers: contacts
        });
      } else {
        await api.createBrand({
          name,
          legal_name: legalName,
          description,
          official_domains: domains,
          official_socials: socials,
          official_apps: apps,
          authorized_publishers: publishers,
          contact_identifiers: contacts
        });
      }
      setModalOpen(false);
      await fetchBrands();
    } catch (err) {
      console.error("Failed to save brand", err);
      setErrorMessage(apiErrorMessage(err, 'Brand changes could not be saved. Check your access and try again.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to remove this protected brand profile?")) {
      setErrorMessage('');
      setDeletingBrandId(id);
      try {
        await api.deleteBrand(id);
        await fetchBrands();
      } catch (err) {
        console.error('Failed to delete brand', err);
        setErrorMessage(apiErrorMessage(err, 'Brand could not be deleted. Please retry.'));
      } finally {
        setDeletingBrandId(null);
      }
    }
  };

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-[#102447]">Trusted Brand Identity Registry</h1>
          <p className="text-xs text-[#657792] mt-0.5">
            Registered baseline of official domains, social handles, apps, and authorized publishers for threat matching
          </p>
        </div>

        <button
          onClick={openCreateModal}
          className="px-4 py-2 bg-[#087CF0] hover:bg-[#076ecc] text-white text-xs font-bold rounded-xl shadow-sm flex items-center gap-1.5 transition-colors"
        >
          <Plus className="w-4 h-4" />
          <span>Register New Brand</span>
        </button>
      </div>

      {errorMessage && (
        <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
          <span>{errorMessage}</span>
          {!loading && brands.length === 0 ? (
            <button type="button" onClick={() => void fetchBrands()} className="font-bold underline">Retry</button>
          ) : null}
        </div>
      )}

      {/* Brand Profile Cards */}
      {loading ? (
        <p className="rounded-2xl border border-[#DCE7F5] bg-white p-8 text-center text-sm text-[#657792]">Loading registered brands…</p>
      ) : brands.length === 0 && !errorMessage ? (
        <p className="rounded-2xl border border-[#DCE7F5] bg-white p-8 text-center text-sm text-[#657792]">No brand records are registered for this organization.</p>
      ) : <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {brands.map((brand) => (
          <div key={brand.id} className="bg-white rounded-2xl border border-[#DCE7F5] shadow-card p-6 space-y-4">

            {/* Title & Verification Badge */}
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-3">
                <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[#087CF0] to-[#06C8F9] text-white flex items-center justify-center font-bold text-lg shadow-sm">
                  {brand.name[0]}
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <h3 className="text-sm font-bold text-[#102447]">{brand.name}</h3>
                    {brand.is_verified && <CheckCircle2 className="w-4 h-4 text-emerald-500 fill-emerald-100" />}
                  </div>
                  <p className="text-[11px] text-[#657792]">{brand.legal_name || 'Legal name not recorded'}</p>
                  <p className={`text-[10px] font-semibold ${brand.is_verified ? 'text-emerald-700' : 'text-amber-700'}`}>
                    {brand.is_verified ? 'Admin-marked verified' : 'Unverified owner-submitted claims'}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => openEditModal(brand)}
                  className="p-1.5 text-[#657792] hover:text-[#087CF0] rounded-lg hover:bg-[#F1F7FF]"
                >
                  <Edit className="w-4 h-4" />
                </button>
                <button
                  onClick={() => handleDelete(brand.id)}
                  disabled={deletingBrandId !== null || saving}
                  className="p-1.5 text-[#657792] hover:text-red-600 rounded-lg hover:bg-red-50"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>

            <p className="text-xs text-[#657792] leading-relaxed">
              {brand.description}
            </p>

            {/* Asset Breakdown */}
            <div className="space-y-2.5 pt-2 border-t border-gray-100 text-xs">

              {/* Domains */}
              <div>
                <p className="text-[10px] font-bold text-[#657792] uppercase flex items-center gap-1 mb-1">
                  <Globe className="w-3 h-3 text-[#087CF0]" /> Registered Domains
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {brand.official_domains.map((d, i) => (
                    <span key={i} className="px-2 py-0.5 bg-[#F1F7FF] text-[#087CF0] border border-[#D0E4FA] rounded-md text-[11px] font-mono">
                      {d}
                    </span>
                  ))}
                </div>
              </div>

              {/* Social Accounts */}
              <div>
                <p className="text-[10px] font-bold text-[#657792] uppercase flex items-center gap-1 mb-1">
                  <UserX className="w-3 h-3 text-[#12B981]" /> Authorized Social Handles
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {brand.official_socials.map((s, i) => (
                    <span key={i} className="px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-md text-[11px]">
                      {s.platform}: {s.handle}{s.url ? ` · ${s.url}` : ''}
                    </span>
                  ))}
                </div>
              </div>

              {/* Mobile Apps */}
              <div>
                <p className="text-[10px] font-bold text-[#657792] uppercase flex items-center gap-1 mb-1">
                  <Smartphone className="w-3 h-3 text-[#8B5CF6]" /> Official Mobile Apps
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {brand.official_apps.map((a, i) => (
                    <span key={i} className="px-2 py-0.5 bg-purple-50 text-purple-700 border border-purple-200 rounded-md text-[11px]">
                      {a.name} ({a.package_id || 'Package ID not recorded'})
                      {a.developer ? ` · Publisher: ${a.developer}` : ''}
                    </span>
                  ))}
                </div>
              </div>

              <BrandImageReferences brand={brand} />

            </div>

          </div>
        ))}
      </div>}

      {/* Create / Edit Modal */}
      {modalOpen && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-[#DCE7F5] max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-[#DCE7F5] mb-4">
              <h3 className="text-base font-bold text-[#102447]">
                {editingBrand ? 'Edit Protected Brand' : 'Register New Official Brand'}
              </h3>
              <button onClick={() => setModalOpen(false)} disabled={saving} className="text-[#657792] hover:text-black disabled:opacity-50">
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveBrand} className="space-y-3.5">
              <div>
                <label className="text-xs font-bold text-[#102447]">Brand Common Name</label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="State Bank of India (SBI)"
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#102447]">Official Contact Identifiers</label>
                <input
                  type="text"
                  value={contactsInput}
                  onChange={(e) => setContactsInput(e.target.value)}
                  placeholder="official@example.org, +1 555 0100"
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#102447]">Legal Entity Name</label>
                <input
                  type="text"
                  value={legalName}
                  onChange={(e) => setLegalName(e.target.value)}
                  placeholder="State Bank of India"
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#102447]">Description</label>
                <textarea
                  rows={2}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Public sector statutory banking institution..."
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#102447]">Official Domains (comma separated)</label>
                <input
                  type="text"
                  value={domainsInput}
                  onChange={(e) => setDomainsInput(e.target.value)}
                  placeholder="sbi.co.in, onlinesbi.sbi"
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#102447]">Official Social Accounts (Platform:Handle, comma separated)</label>
                <input
                  type="text"
                  value={socialsInput}
                  onChange={(e) => setSocialsInput(e.target.value)}
                  placeholder="X:@TheOfficialSBI, Facebook:StateBankofIndia"
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#102447]">Official Mobile Apps (Name:PackageId, comma separated)</label>
                <input
                  type="text"
                  value={appsInput}
                  onChange={(e) => setAppsInput(e.target.value)}
                  placeholder="YONO SBI:com.sbi.lotusintouch"
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#102447]">Authorized Publishers</label>
                <input
                  type="text"
                  value={publishersInput}
                  onChange={(e) => setPublishersInput(e.target.value)}
                  placeholder="State Bank of India, SBI Cards"
                  className="w-full px-3 py-2 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs"
                />
              </div>

              <div className="pt-3 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  disabled={saving}
                  className="px-4 py-2 border border-[#DCE7F5] rounded-xl text-xs font-bold text-[#657792]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="px-4 py-2 bg-[#087CF0] hover:bg-[#076ecc] disabled:opacity-60 text-white rounded-xl text-xs font-bold shadow-md"
                >
                  {saving ? 'Saving…' : 'Save Brand'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
};

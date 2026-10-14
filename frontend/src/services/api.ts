import axios from 'axios';
import {
  User, BrandProfile, Investigation, Alert, Campaign,
  AnalysisResult, ThreatGraphNode, ThreatGraphLink, InvestigationReport,
  CampaignClusterSuggestion, BrandImageReference
} from '../types';

const API_BASE = `${(import.meta.env.VITE_API_URL || '').replace(/\/+$/, '')}/api/v1`;  

const apiClient = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const api = {
  // Auth
  login: async (credentials: { username_or_email: string; password: string }) => {
    const res = await apiClient.post<{ access_token: string; user: User }>('/auth/login', credentials);
    return res.data;
  },
  register: async (userData: any) => {
    const res = await apiClient.post<User>('/auth/register', userData);
    return res.data;
  },
  getMe: async () => {
    const res = await apiClient.get<User>('/auth/me');
    return res.data;
  },

  // Dashboard
  getDashboardStats: async () => {
    const res = await apiClient.get<any>('/dashboard/stats');
    return res.data;
  },

  // Analysis
  analyzeUrl: async (url: string, brandId?: string) => {
    const res = await apiClient.post<AnalysisResult>('/analysis/url', { url, brand_id: brandId });
    return res.data;
  },
  analyzeProfile: async (data: { platform: string; handle?: string; display_name?: string; profile_url?: string; bio_text?: string; brand_id?: string }) => {
    const res = await apiClient.post<AnalysisResult>('/analysis/profile', data);
    return res.data;
  },
  analyzeApp: async (data: { app_name: string; package_name?: string; developer_name?: string; store_url?: string; description?: string; brand_id?: string }) => {
    const res = await apiClient.post<AnalysisResult>('/analysis/app', data);
    return res.data;
  },
  analyzeMessage: async (data: { message_text: string; sender_identifier?: string; brand_id?: string }) => {
    const res = await apiClient.post<AnalysisResult>('/analysis/message', data);
    return res.data;
  },
  analyzeImage: async (formData: FormData) => {
    const res = await apiClient.post<AnalysisResult>('/analysis/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return res.data;
  },

  // Brands
  getBrands: async () => {
    const res = await apiClient.get<BrandProfile[]>('/brands');
    return res.data;
  },
  createBrand: async (brand: Partial<BrandProfile>) => {
    const res = await apiClient.post<BrandProfile>('/brands', brand);
    return res.data;
  },
  updateBrand: async (id: string, brand: Partial<BrandProfile>) => {
    const res = await apiClient.patch<BrandProfile>(`/brands/${id}`, brand);
    return res.data;
  },
  deleteBrand: async (id: string) => {
    const res = await apiClient.delete(`/brands/${id}`);
    return res.data;
  },
  getBrandImageReferences: async (brandId: string) => {
    const res = await apiClient.get<{ items: BrandImageReference[] }>(
      `/brands/${brandId}/image-references`
    );
    return res.data.items;
  },
  uploadBrandImageReference: async (brandId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.post<BrandImageReference>(
      `/brands/${brandId}/image-references`, formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return res.data;
  },
  replaceBrandImageReference: async (brandId: string, referenceId: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await apiClient.put<BrandImageReference>(
      `/brands/${brandId}/image-references/${referenceId}`, formData,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return res.data;
  },
  removeBrandImageReference: async (brandId: string, referenceId: string) => {
    await apiClient.delete(`/brands/${brandId}/image-references/${referenceId}`);
  },

  // Investigations
  getInvestigations: async (params?: { type?: string; status?: string; search?: string }) => {
    const res = await apiClient.get<Investigation[]>('/investigations', { params });
    return res.data;
  },
  createInvestigation: async (data: any) => {
    const res = await apiClient.post<Investigation>('/investigations', data);
    return res.data;
  },
  getInvestigation: async (id: string) => {
    const res = await apiClient.get<Investigation>(`/investigations/${id}`);
    return res.data;
  },
  updateInvestigation: async (id: string, data: Partial<Investigation> & { disposition_reason?: string }) => {
    const res = await apiClient.patch<Investigation>(`/investigations/${id}`, data);
    return res.data;
  },

  // Alerts
  getAlerts: async (params?: { severity?: string; status?: string }) => {
    const res = await apiClient.get<Alert[]>('/alerts', { params });
    return res.data;
  },
  updateAlert: async (id: string, status: string) => {
    const res = await apiClient.patch<Alert>(`/alerts/${id}`, { status });
    return res.data;
  },

  // Campaigns
  getCampaigns: async () => {
    const res = await apiClient.get<Campaign[]>('/campaigns');
    return res.data;
  },
  getCampaignClusterSuggestions: async () => {
    const res = await apiClient.get<{
      mode: string;
      suggestions: CampaignClusterSuggestion[];
    }>('/campaigns/cluster-suggestions');
    return res.data;
  },

  // Threat Graph
  getThreatGraph: async () => {
    const res = await apiClient.get<{ nodes: ThreatGraphNode[]; links: ThreatGraphLink[] }>('/threat-graph');
    return res.data;
  },

  // Safety Copilot
  copilotChat: async (message: string, language: string = 'en') => {
    const res = await apiClient.post<{ reply: string; language: string; safety_tips: string[]; suggested_actions: string[]; risk_assessment?: string }>(
      '/copilot/chat',
      { message, language }
    );
    return res.data;
  },

  // Reports
  getReports: async () => {
    const res = await apiClient.get<InvestigationReport[]>('/reports');
    return res.data;
  },
  downloadReport: async (caseId: string) => {
    const res = await apiClient.get<Blob>(`/reports/${caseId}/download-csv`, {
      responseType: 'blob',
    });
    return res.data;
  },

  // Settings
  getSettings: async () => {
    const res = await apiClient.get<any>('/settings');
    return res.data;
  }
};

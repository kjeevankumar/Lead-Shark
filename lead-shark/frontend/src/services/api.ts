import axios from 'axios';
import { 
  User, Lead, DiscoveryJob, DiscoveryResultItem, Campaign, SuppressionRecord, 
  AuditLogItem, OverviewStatistics, CampaignAnalyticsItem, UserRole 
} from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Attach authorization token if stored
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('leadshark_token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const api = {
  // Health
  checkHealth: async () => {
    const res = await client.get('/health');
    return res.data;
  },

  // Auth
  login: async (email: string, password: string = 'LeadShark2026!') => {
    const res = await client.post('/api/auth/login', { email, password });
    if (res.data?.access_token) {
      localStorage.setItem('leadshark_token', res.data.access_token);
      localStorage.setItem('leadshark_user', JSON.stringify(res.data.user));
    }
    return res.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const res = await client.get('/api/auth/me');
    return res.data;
  },

  switchDemoRole: async (role: UserRole) => {
    const res = await client.post('/api/auth/switch-demo-role', { role });
    if (res.data?.access_token) {
      localStorage.setItem('leadshark_token', res.data.access_token);
      localStorage.setItem('leadshark_user', JSON.stringify(res.data.user));
    }
    return res.data;
  },

  // Discovery
  listDiscoveryJobs: async (): Promise<DiscoveryJob[]> => {
    const res = await client.get('/api/discovery/jobs');
    return res.data;
  },

  createDiscoveryJob: async (data: {
    job_name?: string;
    source: string;
    query: string;
    region?: string;
    industry?: string;
    max_results?: number;
    schedule?: string;
  }): Promise<DiscoveryJob> => {
    const res = await client.post('/api/discovery/jobs', data);
    return res.data;
  },

  getDiscoveryJobResults: async (jobId: string): Promise<DiscoveryResultItem[]> => {
    const res = await client.get(`/api/discovery/jobs/${jobId}/results`);
    return res.data;
  },

  // Leads
  listLeads: async (params?: {
    search?: string;
    sector?: string;
    region?: string;
    verification_status?: string;
    source_type?: string;
    status?: string;
  }): Promise<Lead[]> => {
    const res = await client.get('/api/leads', { params });
    return res.data;
  },

  getLead: async (id: string): Promise<Lead> => {
    const res = await client.get(`/api/leads/${id}`);
    return res.data;
  },

  importLeadsCsv: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await client.post('/api/leads/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
  },

  verifyLeads: async (params?: { lead_id?: string; verify_all_unverified?: boolean }) => {
    const res = await client.post('/api/leads/verify', null, { params });
    return res.data;
  },

  classifyLeads: async (params?: { lead_id?: string; classify_all_unclassified?: boolean }) => {
    const res = await client.post('/api/leads/classify', null, { params });
    return res.data;
  },

  approveLead: async (id: string) => {
    const res = await client.post(`/api/leads/${id}/approve`);
    return res.data;
  },

  rejectLead: async (id: string) => {
    const res = await client.post(`/api/leads/${id}/reject`);
    return res.data;
  },

  bulkAction: async (leadIds: string[], action: string) => {
    const res = await client.post('/api/leads/bulk-action', { lead_ids: leadIds, action });
    return res.data;
  },

  deleteLeadByEmail: async (email: string) => {
    const res = await client.delete('/api/leads/by-email', { data: { email } });
    return res.data;
  },

  // Campaigns
  listCampaigns: async (): Promise<Campaign[]> => {
    const res = await client.get('/api/campaigns');
    return res.data;
  },

  createCampaign: async (data: {
    name: string;
    target_sector: string;
    target_region?: string;
    subject: string;
    body: string;
    daily_limit?: number;
    steps?: any[];
  }): Promise<Campaign> => {
    const res = await client.post('/api/campaigns', data);
    return res.data;
  },

  updateCampaign: async (id: string, data: Partial<Campaign>): Promise<Campaign> => {
    const res = await client.put(`/api/campaigns/${id}`, data);
    return res.data;
  },

  submitForApproval: async (id: string) => {
    const res = await client.post(`/api/campaigns/${id}/submit-for-approval`);
    return res.data;
  },

  approveCampaign: async (id: string) => {
    const res = await client.post(`/api/campaigns/${id}/approve`);
    return res.data;
  },

  pauseCampaign: async (id: string) => {
    const res = await client.post(`/api/campaigns/${id}/pause`);
    return res.data;
  },

  resumeCampaign: async (id: string) => {
    const res = await client.post(`/api/campaigns/${id}/resume`);
    return res.data;
  },

  previewCampaign: async (id: string, sampleLeadId?: string) => {
    const res = await client.post(`/api/campaigns/${id}/preview`, { sample_lead_id: sampleLeadId });
    return res.data;
  },

  sendCampaignBatch: async (id: string, batchSize: number = 3) => {
    const res = await client.post(`/api/campaigns/${id}/send-batch?batch_size=${batchSize}`);
    return res.data;
  },

  // Compliance
  getSuppressionList: async (): Promise<SuppressionRecord[]> => {
    const res = await client.get('/api/compliance/suppression');
    return res.data;
  },

  addSuppression: async (data: { email?: string; domain?: string; reason: string }): Promise<SuppressionRecord> => {
    const res = await client.post('/api/compliance/suppression', data);
    return res.data;
  },

  deleteSuppression: async (id: string) => {
    const res = await client.delete(`/api/compliance/suppression/${id}`);
    return res.data;
  },

  getDnsHealth: async () => {
    const res = await client.get('/api/compliance/dns-health');
    return res.data;
  },

  publicUnsubscribe: async (token: string) => {
    const res = await client.post(`/unsubscribe/${token}`);
    return res.data;
  },

  // Analytics & Audit
  getOverviewAnalytics: async (): Promise<OverviewStatistics> => {
    const res = await client.get('/api/analytics/overview');
    return res.data;
  },

  getCampaignAnalytics: async (): Promise<CampaignAnalyticsItem[]> => {
    const res = await client.get('/api/analytics/campaigns');
    return res.data;
  },

  getExportCsvUrl: () => `${API_BASE}/api/analytics/export-csv`,

  getAuditLogs: async (): Promise<AuditLogItem[]> => {
    const res = await client.get('/api/audit-logs');
    return res.data;
  },

  triggerEmailWebhookEvent: async (data: {
    type: string;
    email?: string;
    campaign_id?: string;
    details?: string;
  }) => {
    const res = await client.post('/webhooks/email-events', data);
    return res.data;
  }
};

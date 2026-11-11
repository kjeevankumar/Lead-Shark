export type UserRole = 'admin' | 'reviewer' | 'sales';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
}

export interface Company {
  id: string;
  name: string;
  domain: string;
  website?: string;
  phone?: string;
  address?: string;
  sector?: string;
  description?: string;
  created_at: string;
}

export type EmailStatus = 'valid' | 'risky' | 'invalid' | 'unknown';
export type LeadStatus = 'new' | 'verified' | 'approved' | 'contacted' | 'replied' | 'bounced' | 'suppressed' | 'rejected';

export interface Lead {
  id: string;
  company_id?: string;
  company?: Company;
  name?: string;
  title?: string;
  email: string;
  email_status: EmailStatus;
  email_details?: string;
  region?: string;
  industry?: string;
  sector?: string;
  sector_confidence: number;
  sector_reason?: string;
  source_type: string;
  source_url?: string;
  lawful_basis_note?: string;
  status: LeadStatus;
  unsubscribe_token?: string;
  collected_at: string;
  created_at: string;
  updated_at: string;
}

export interface DiscoveryJob {
  id: string;
  job_name: string;
  source: string;
  query: string;
  region?: string;
  max_results: number;
  schedule: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  total_found: number;
  new_leads_count: number;
  duplicates_skipped: number;
  error_message?: string;
  last_run: string;
  created_at: string;
}

export interface CampaignStep {
  step_no: number;
  delay_days: number;
  subject: string;
  body: string;
}

export type CampaignStatus = 'draft' | 'pending_approval' | 'approved' | 'scheduled' | 'sending' | 'paused' | 'completed';

export interface Campaign {
  id: string;
  name: string;
  target_sector: string;
  target_region?: string;
  subject: string;
  body: string;
  status: CampaignStatus;
  daily_limit: number;
  total_sends: number;
  created_by: string;
  approved_by?: string;
  created_at: string;
  updated_at: string;
  steps?: CampaignStep[];
}

export interface SuppressionRecord {
  id: string;
  email?: string;
  domain?: string;
  reason: string;
  added_at: string;
}

export interface AuditLogItem {
  id: string;
  actor: string;
  action: string;
  object: string;
  details?: string;
  timestamp: string;
}

export interface OverviewStatistics {
  total_leads: number;
  verified_emails: number;
  approved_leads: number;
  active_campaigns: number;
  emails_sent: number;
  delivery_rate: number;
  reply_rate: number;
  bounce_rate: number;
  complaint_rate: number;
  unsubscribed_count: number;
  sector_distribution: { sector: string; count: number }[];
  status_distribution: { status: string; count: number }[];
}

export interface CampaignAnalyticsItem {
  id: string;
  name: string;
  sector: string;
  status: string;
  daily_limit: number;
  sends: number;
  opens: number;
  replies: number;
  bounces: number;
  unsubscribes: number;
  created_at: string;
}

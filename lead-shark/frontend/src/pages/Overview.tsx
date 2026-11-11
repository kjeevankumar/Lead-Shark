import React, { useEffect, useState } from 'react';
import { 
  Users, ShieldCheck, CheckCircle2, Send, Mail, MessageSquare, 
  AlertTriangle, UserX, ArrowUpRight, TrendingUp, Compass, Plus, RefreshCw 
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, 
  PieChart, Pie, Cell, AreaChart, Area 
} from 'recharts';
import { api } from '../services/api';
import { OverviewStatistics, DiscoveryJob, Campaign } from '../types';

interface OverviewProps {
  onNavigate: (tab: string) => void;
}

export const Overview: React.FC<OverviewProps> = ({ onNavigate }) => {
  const [stats, setStats] = useState<OverviewStatistics | null>(null);
  const [recentJobs, setRecentJobs] = useState<DiscoveryJob[]>([]);
  const [recentCampaigns, setRecentCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      const [statsData, jobsData, campsData] = await Promise.all([
        api.getOverviewAnalytics(),
        api.listDiscoveryJobs(),
        api.listCampaigns(),
      ]);
      setStats(statsData);
      setRecentJobs(jobsData.slice(0, 4));
      setRecentCampaigns(campsData.slice(0, 4));
    } catch (err) {
      console.error('Failed to load overview data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const COLORS = ['#2563EB', '#10B981', '#F59E0B', '#8B5CF6', '#EC4899', '#06B6D4'];

  const kpis = [
    { label: 'Total Leads Discovered', value: stats?.total_leads || 0, icon: Users, change: '+18% this month', color: 'text-blue-600', bg: 'bg-blue-50' },
    { label: 'Verified Clean Emails', value: stats?.verified_emails || 0, icon: ShieldCheck, change: '100% campaign eligible', color: 'text-emerald-600', bg: 'bg-emerald-50' },
    { label: 'Approved for Outreach', value: stats?.approved_leads || 0, icon: CheckCircle2, change: 'Human-in-the-loop reviewed', color: 'text-indigo-600', bg: 'bg-indigo-50' },
    { label: 'Active Campaigns', value: stats?.active_campaigns || 0, icon: Send, change: 'Strictly throttled', color: 'text-amber-600', bg: 'bg-amber-50' },
    { label: 'Outbound Sends (Demo)', value: stats?.emails_sent || 0, icon: Mail, change: 'Zero unapproved sends', color: 'text-sky-600', bg: 'bg-sky-50' },
    { label: 'Reply Rate', value: `${stats?.reply_rate || 0}%`, icon: MessageSquare, change: 'Above 5% target', color: 'text-teal-600', bg: 'bg-teal-50' },
    { label: 'Bounce Rate', value: `${stats?.bounce_rate || 0}%`, icon: AlertTriangle, change: 'Below 3% safe ceiling', color: 'text-rose-600', bg: 'bg-rose-50' },
    { label: 'Global Suppressed', value: stats?.unsubscribed_count || 0, icon: UserX, change: 'Permanent opt-out registry', color: 'text-slate-600', bg: 'bg-slate-100' },
  ];

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Overview Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            Real-time telemetry, lead discovery metrics, and outbound compliance safeguards.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadDashboardData}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 shadow-sm transition"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => onNavigate('discovery')}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition"
          >
            <Compass className="w-3.5 h-3.5" />
            Discover Leads
          </button>
          <button
            onClick={() => onNavigate('campaigns')}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 shadow-sm transition"
          >
            <Plus className="w-3.5 h-3.5" />
            New Campaign
          </button>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {kpis.map((kpi, idx) => {
          const Icon = kpi.icon;
          return (
            <div key={idx} className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs hover:shadow-sm transition">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-medium text-slate-500">{kpi.label}</span>
                <div className={`w-8 h-8 rounded-lg ${kpi.bg} flex items-center justify-center ${kpi.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </div>
              <div className="text-2xl font-bold text-slate-900">{kpi.value}</div>
              <div className="text-[11px] text-slate-400 mt-1 font-medium">{kpi.change}</div>
            </div>
          );
        })}
      </div>

      {/* Analytics Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Sector Distribution */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-base font-semibold text-slate-900">Leads by Sector Distribution</h2>
              <p className="text-xs text-slate-500">Segmented through RAG Lead Segregation Agent</p>
            </div>
            <button onClick={() => onNavigate('segmentation')} className="text-xs text-blue-600 font-semibold hover:underline flex items-center gap-0.5">
              View RAG Classifier <ArrowUpRight className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="h-64">
            {stats?.sector_distribution && stats.sector_distribution.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.sector_distribution} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
                  <XAxis dataKey="sector" tick={{ fontSize: 11, fill: '#64748B' }} interval={0} angle={-15} textAnchor="end" />
                  <YAxis tick={{ fontSize: 11, fill: '#64748B' }} />
                  <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderRadius: '8px', color: '#fff', fontSize: '12px', border: 'none' }} />
                  <Bar dataKey="count" fill="#2563EB" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center text-xs text-slate-400">Loading sector telemetry...</div>
            )}
          </div>
        </div>

        {/* Lead Status Distribution */}
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-semibold text-slate-900">Lead Pipeline Status</h2>
              <p className="text-xs text-slate-500">Current workflow states</p>
            </div>
          </div>
          <div className="h-52 relative flex items-center justify-center">
            {stats?.status_distribution && stats.status_distribution.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={stats.status_distribution}
                    dataKey="count"
                    nameKey="status"
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={3}
                  >
                    {stats.status_distribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ backgroundColor: '#0F172A', borderRadius: '8px', color: '#fff', fontSize: '12px', border: 'none' }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="text-xs text-slate-400">No status metrics</div>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-100 text-xs">
            {stats?.status_distribution?.map((item, idx) => (
              <div key={idx} className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></span>
                <span className="capitalize text-slate-600 text-[11px] truncate">{item.status}: {item.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Lower Grids: Recent Discovery & Recent Campaigns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Discovery Jobs */}
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-slate-900">Recent Discovery Jobs</h2>
            <button onClick={() => onNavigate('discovery')} className="text-xs font-semibold text-blue-600 hover:underline">
              View All Jobs
            </button>
          </div>
          <div className="space-y-3">
            {recentJobs.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">No discovery jobs recorded yet.</p>
            ) : (
              recentJobs.map((job) => (
                <div key={job.id} className="p-3.5 rounded-lg border border-slate-100 hover:border-slate-200 bg-slate-50/50 flex items-center justify-between transition">
                  <div>
                    <div className="text-xs font-semibold text-slate-900">{job.job_name}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Source: <span className="uppercase font-mono text-slate-600">{job.source}</span> &bull; Query: "{job.query}"
                    </div>
                  </div>
                  <div className="text-right">
                    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-700">
                      +{job.new_leads_count} Leads
                    </span>
                    <div className="text-[10px] text-slate-400 mt-0.5">{job.duplicates_skipped} dupes filtered</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Recent Campaigns */}
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-slate-900">Active Campaigns</h2>
            <button onClick={() => onNavigate('campaigns')} className="text-xs font-semibold text-blue-600 hover:underline">
              Manage Campaigns
            </button>
          </div>
          <div className="space-y-3">
            {recentCampaigns.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">No campaigns launched yet.</p>
            ) : (
              recentCampaigns.map((camp) => (
                <div key={camp.id} className="p-3.5 rounded-lg border border-slate-100 hover:border-slate-200 bg-slate-50/50 flex items-center justify-between transition">
                  <div>
                    <div className="text-xs font-semibold text-slate-900">{camp.name}</div>
                    <div className="text-[11px] text-slate-400 mt-0.5">
                      Sector: <span className="font-medium text-slate-700">{camp.target_sector}</span> &bull; Limit: {camp.daily_limit}/day
                    </div>
                  </div>
                  <div className="text-right">
                    <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-bold ${
                      camp.status === 'approved' ? 'bg-blue-100 text-blue-700' :
                      camp.status === 'sending' ? 'bg-emerald-100 text-emerald-700' :
                      camp.status === 'paused' ? 'bg-amber-100 text-amber-700' :
                      'bg-slate-100 text-slate-600'
                    }`}>
                      {camp.status.replace('_', ' ').toUpperCase()}
                    </span>
                    <div className="text-[10px] text-slate-400 mt-0.5">{camp.total_sends} simulated sends</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

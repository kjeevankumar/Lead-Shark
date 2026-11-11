import React, { useState, useEffect } from 'react';
import { 
  ShieldCheck, CheckCircle2, AlertTriangle, XCircle, 
  RefreshCw, Play, Filter, Check, Mail, Server 
} from 'lucide-react';
import { api } from '../services/api';
import { Lead } from '../types';

export const EnrichmentVerification: React.FC = () => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState<string>('All');
  const [verificationFeedback, setVerificationFeedback] = useState<any>(null);

  const fetchLeads = async () => {
    try {
      setLoading(true);
      const data = await api.listLeads({
        verification_status: filterStatus !== 'All' ? filterStatus : undefined,
      });
      setLeads(data);
    } catch (err) {
      console.error('Error fetching leads:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [filterStatus]);

  const handleRunBatchVerification = async () => {
    try {
      setLoading(true);
      const res = await api.verifyLeads({ verify_all_unverified: true });
      setVerificationFeedback(res);
      await fetchLeads();
    } catch (err) {
      alert('Verification failed');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifySingle = async (leadId: string) => {
    try {
      setLoading(true);
      await api.verifyLeads({ lead_id: leadId });
      await fetchLeads();
    } catch (err) {
      alert('Single verification failed');
    } finally {
      setLoading(false);
    }
  };

  const counts = {
    valid: leads.filter((l) => l.email_status === 'valid').length,
    risky: leads.filter((l) => l.email_status === 'risky').length,
    invalid: leads.filter((l) => l.email_status === 'invalid').length,
    unknown: leads.filter((l) => l.email_status === 'unknown').length,
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Enrichment & Email Verification</h1>
          <p className="text-sm text-slate-500 mt-1">
            Deterministic multi-layer email deliverability validation, DNS/MX check, and anti-spam protection.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRunBatchVerification}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-50"
          >
            <ShieldCheck className="w-4 h-4" />
            {loading ? 'Verifying MX & Syntax...' : 'Run Verification on Unverified Leads'}
          </button>
        </div>
      </div>

      {/* Rules Breakdown Card */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center gap-2 mb-2 text-emerald-600 font-semibold text-xs">
            <CheckCircle2 className="w-4 h-4" />
            <span>Valid Corporate</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">{counts.valid}</div>
          <p className="text-[11px] text-slate-500 mt-1">
            Confirmed MX records, valid syntax, genuine domain. Campaign eligible.
          </p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center gap-2 mb-2 text-amber-600 font-semibold text-xs">
            <AlertTriangle className="w-4 h-4" />
            <span>Risky (Freemail / Role)</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">{counts.risky}</div>
          <p className="text-[11px] text-slate-500 mt-1">
            Consumer freemails (Gmail/Yahoo) excluded from cold outreach; role-based tagged.
          </p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center gap-2 mb-2 text-rose-600 font-semibold text-xs">
            <XCircle className="w-4 h-4" />
            <span>Invalid / Bad MX</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">{counts.invalid}</div>
          <p className="text-[11px] text-slate-500 mt-1">
            No DNS/MX records or invalid syntax. Blocked from all sends permanently.
          </p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs">
          <div className="flex items-center gap-2 mb-2 text-slate-500 font-semibold text-xs">
            <RefreshCw className="w-4 h-4" />
            <span>Pending Verification</span>
          </div>
          <div className="text-2xl font-bold text-slate-900">{counts.unknown}</div>
          <p className="text-[11px] text-slate-500 mt-1">
            Freshly imported or discovered leads awaiting deliverability screening.
          </p>
        </div>
      </div>

      {/* Verification Feedback Banner */}
      {verificationFeedback && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-900 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Check className="w-4 h-4 text-emerald-600" />
            <span>
              Batch verified <strong>{verificationFeedback.verified_count}</strong> leads: 
              {' '}{verificationFeedback.valid_count} valid, {verificationFeedback.risky_count} risky, {verificationFeedback.invalid_count} invalid.
            </span>
          </div>
          <button onClick={() => setVerificationFeedback(null)} className="text-emerald-700 hover:text-emerald-900 font-bold">
            &times;
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-2 text-xs font-medium">
        {['All', 'valid', 'risky', 'invalid', 'unknown'].map((st) => (
          <button
            key={st}
            onClick={() => setFilterStatus(st)}
            className={`px-3 py-1.5 rounded-lg capitalize transition ${
              filterStatus === st ? 'bg-slate-900 text-white font-semibold' : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {st} ({st === 'All' ? leads.length : counts[st as keyof typeof counts] || 0})
          </button>
        ))}
      </div>

      {/* Leads Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50/70 border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              <tr>
                <th className="px-5 py-3.5">Contact & Company</th>
                <th className="px-5 py-3.5">Email Address</th>
                <th className="px-5 py-3.5">Verification Status</th>
                <th className="px-5 py-3.5">Deliverability Diagnostics</th>
                <th className="px-5 py-3.5">Campaign Eligible</th>
                <th className="px-5 py-3.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {leads.map((l) => {
                const details = l.email_details ? JSON.parse(l.email_details) : null;
                const isCampaignEligible = l.email_status === 'valid';

                return (
                  <tr key={l.id} className="hover:bg-slate-50/50">
                    <td className="px-5 py-3.5">
                      <div className="font-semibold text-slate-900">{l.name}</div>
                      <div className="text-[11px] text-slate-400">{l.company?.name || 'Company'}</div>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-slate-800 font-medium">{l.email}</td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                        l.email_status === 'valid' ? 'bg-emerald-100 text-emerald-800' :
                        l.email_status === 'risky' ? 'bg-amber-100 text-amber-800' :
                        l.email_status === 'invalid' ? 'bg-rose-100 text-rose-800' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {l.email_status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-600 text-[11px]">
                      {details?.reason || (l.email_status === 'valid' ? 'Valid MX host verified' : 'Awaiting check')}
                    </td>
                    <td className="px-5 py-3.5">
                      {isCampaignEligible ? (
                        <span className="text-emerald-600 font-bold flex items-center gap-1">
                          <Check className="w-3.5 h-3.5" /> Eligible
                        </span>
                      ) : (
                        <span className="text-slate-400 font-medium">Excluded</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={() => handleVerifySingle(l.id)}
                        className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-800 rounded font-medium text-[11px] transition"
                      >
                        Re-verify
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

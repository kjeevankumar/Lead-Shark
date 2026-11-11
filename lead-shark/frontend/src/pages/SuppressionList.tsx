import React, { useState, useEffect } from 'react';
import { Ban, ShieldAlert, Plus, Trash2, RefreshCw, UserX, Globe, Mail } from 'lucide-react';
import { api } from '../services/api';
import { SuppressionRecord, UserRole } from '../types';

interface SuppressionListProps {
  currentRole: UserRole;
}

export const SuppressionList: React.FC<SuppressionListProps> = ({ currentRole }) => {
  const [suppressions, setSuppressions] = useState<SuppressionRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);

  // Form
  const [suppressType, setSuppressType] = useState<'email' | 'domain'>('email');
  const [value, setValue] = useState('');
  const [reason, setReason] = useState('unsubscribed');

  // GDPR Erasure Form
  const [erasureEmail, setErasureEmail] = useState('');
  const [erasureFeedback, setErasureFeedback] = useState<string | null>(null);

  const fetchSuppressions = async () => {
    try {
      setLoading(true);
      const data = await api.getSuppressionList();
      setSuppressions(data);
    } catch (err) {
      console.error('Failed to load suppression list:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSuppressions();
  }, []);

  const handleAddSuppression = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!value) return;

    try {
      setLoading(true);
      await api.addSuppression({
        email: suppressType === 'email' ? value.trim().toLowerCase() : undefined,
        domain: suppressType === 'domain' ? value.trim().toLowerCase() : undefined,
        reason,
      });
      setShowAddModal(false);
      setValue('');
      await fetchSuppressions();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to add suppression entry');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteEntry = async (id: string) => {
    if (currentRole !== 'admin') {
      alert('Only Admin users can remove records from global suppression.');
      return;
    }
    const confirmDel = window.confirm('Are you sure you want to remove this contact from global suppression?');
    if (!confirmDel) return;

    try {
      await api.deleteSuppression(id);
      await fetchSuppressions();
    } catch (err) {
      alert('Failed to remove suppression');
    }
  };

  const handleExecuteErasure = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!erasureEmail) return;
    if (currentRole !== 'admin') {
      alert('GDPR Right to Erasure execution requires Admin role privileges.');
      return;
    }

    try {
      setLoading(true);
      const res = await api.deleteLeadByEmail(erasureEmail);
      setErasureFeedback(res.message);
      setErasureEmail('');
      await fetchSuppressions();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Data erasure request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Global Suppression & Opt-Out Registry</h1>
          <p className="text-sm text-slate-500 mt-1">
            Permanent exclusion database. Every send is validated against this list before dispatch.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchSuppressions}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-slate-900 rounded-lg hover:bg-slate-800 shadow-sm"
          >
            <Plus className="w-3.5 h-3.5" />
            Add Suppression Record
          </button>
        </div>
      </div>

      {/* Compliance Callout Banner */}
      <div className="p-4 rounded-xl bg-slate-900 text-slate-100 flex items-start gap-3 shadow-md">
        <ShieldAlert className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
        <div className="text-xs space-y-1">
          <div className="font-bold text-white text-sm">Pre-Send Enforcement Guarantee</div>
          <p className="text-slate-300 leading-relaxed">
            Lead Shark executes an atomic query check before every message. Any email or domain present in this registry will be unconditionally blocked from receiving outreach, satisfying CAN-SPAM, GDPR Article 21 (Right to Object), and the India DPDP Act.
          </p>
        </div>
      </div>

      {/* GDPR Data Erasure Box */}
      <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <UserX className="w-5 h-5 text-rose-600" />
            <h2 className="text-base font-semibold text-slate-900">GDPR Art. 17 Data Erasure Tool (Right to Be Forgotten)</h2>
          </div>
          <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 uppercase">
            Admin Only
          </span>
        </div>
        <p className="text-xs text-slate-500 leading-relaxed">
          Submitting an erasure request purges all lead records and contact dossiers for the target address while permanently retaining the email hash in the suppression list to prevent future re-acquisition.
        </p>

        <form onSubmit={handleExecuteErasure} className="flex flex-col sm:flex-row gap-3">
          <input
            type="email"
            required
            placeholder="recipient@corporate.com"
            value={erasureEmail}
            onChange={(e) => setErasureEmail(e.target.value)}
            className="flex-1 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-2 focus:ring-rose-500/20 focus:border-rose-500"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
          >
            Execute Permanent Erasure
          </button>
        </form>

        {erasureFeedback && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs text-emerald-800 font-medium">
            {erasureFeedback}
          </div>
        )}
      </div>

      {/* Suppression Records Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Active Suppressed Records</h2>
            <p className="text-xs text-slate-500">Unsubscribes, hard bounces, complaints, and legal requests</p>
          </div>
          <span className="text-xs font-bold text-slate-700 bg-slate-100 px-2.5 py-1 rounded-full">
            {suppressions.length} Records
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50/70 border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              <tr>
                <th className="px-5 py-3.5">Suppression Target</th>
                <th className="px-5 py-3.5">Type</th>
                <th className="px-5 py-3.5">Reason Code</th>
                <th className="px-5 py-3.5">Timestamp Added</th>
                <th className="px-5 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {suppressions.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-slate-400">
                    No suppression records exist.
                  </td>
                </tr>
              ) : (
                suppressions.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50/50">
                    <td className="px-5 py-3.5 font-mono font-medium text-slate-900">
                      {s.email || `@${s.domain}`}
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-slate-100 text-slate-700">
                        {s.email ? 'Email' : 'Domain-Wide'}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                        s.reason === 'unsubscribed' ? 'bg-blue-100 text-blue-800' :
                        s.reason === 'hard_bounce' ? 'bg-amber-100 text-amber-800' :
                        s.reason === 'complaint' ? 'bg-rose-100 text-rose-800' :
                        'bg-purple-100 text-purple-800'
                      }`}>
                        {s.reason.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 font-mono text-slate-400 text-[11px]">
                      {new Date(s.added_at).toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      {currentRole === 'admin' ? (
                        <button
                          onClick={() => handleDeleteEntry(s.id)}
                          className="text-slate-400 hover:text-rose-600 transition p-1"
                          title="Remove Suppression"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      ) : (
                        <span className="text-[10px] text-slate-400">Locked</span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Suppression Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Add Global Suppression Record</h3>
              <button onClick={() => setShowAddModal(false)} className="text-slate-400 hover:text-slate-700 text-lg font-bold">
                &times;
              </button>
            </div>

            <form onSubmit={handleAddSuppression} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Suppression Level</label>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setSuppressType('email')}
                    className={`py-2 rounded-lg font-semibold border ${
                      suppressType === 'email' ? 'bg-blue-50 border-blue-600 text-blue-700' : 'bg-slate-50 border-slate-200 text-slate-600'
                    }`}
                  >
                    Specific Email
                  </button>
                  <button
                    type="button"
                    onClick={() => setSuppressType('domain')}
                    className={`py-2 rounded-lg font-semibold border ${
                      suppressType === 'domain' ? 'bg-blue-50 border-blue-600 text-blue-700' : 'bg-slate-50 border-slate-200 text-slate-600'
                    }`}
                  >
                    Entire Domain
                  </button>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  {suppressType === 'email' ? 'Email Address' : 'Domain Name'}
                </label>
                <input
                  type="text"
                  required
                  placeholder={suppressType === 'email' ? 'e.g. user@domain.com' : 'e.g. competitor.com'}
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Suppression Reason</label>
                <select
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                >
                  <option value="unsubscribed">Recipient Unsubscribed (Opt-Out)</option>
                  <option value="hard_bounce">Hard Bounce (Undeliverable / Bad Host)</option>
                  <option value="complaint">Spam Complaint</option>
                  <option value="gdpr_request">GDPR Article 17 Erasure Request</option>
                  <option value="manual">Manual Admin Blacklist</option>
                </select>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white font-semibold rounded-lg shadow-sm"
                >
                  Register Suppression
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

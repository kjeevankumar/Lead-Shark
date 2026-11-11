import React, { useState, useEffect } from 'react';
import { 
  Users, CheckCircle2, XCircle, ShieldCheck, Cpu, 
  Trash2, Ban, Eye, RefreshCw, Filter, Download, CheckSquare, Square,
  Search, X
} from 'lucide-react';
import { api } from '../services/api';
import { Lead, UserRole } from '../types';

interface AllLeadsProps {
  currentRole: UserRole;
  globalSearch: string;
}

export const AllLeads: React.FC<AllLeadsProps> = ({ currentRole, globalSearch }) => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // Filters
  const [localSearch, setLocalSearch] = useState('');
  const [sectorFilter, setSectorFilter] = useState('All');
  const [regionFilter, setRegionFilter] = useState('All');
  const [verificationFilter, setVerificationFilter] = useState('All');
  const [statusFilter, setStatusFilter] = useState('All');

  const fetchLeads = async () => {
    try {
      setLoading(true);
      const effectiveSearch = localSearch.trim() || globalSearch.trim() || undefined;
      const data = await api.listLeads({
        search: effectiveSearch,
        sector: sectorFilter !== 'All' ? sectorFilter : undefined,
        region: regionFilter !== 'All' ? regionFilter : undefined,
        verification_status: verificationFilter !== 'All' ? verificationFilter : undefined,
        status: statusFilter !== 'All' ? statusFilter : undefined,
      });
      setLeads(data);
    } catch (err) {
      console.error('Failed to load leads:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, [localSearch, globalSearch, sectorFilter, regionFilter, verificationFilter, statusFilter]);

  const handleSelectAll = () => {
    if (selectedIds.length === leads.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(leads.map((l) => l.id));
    }
  };

  const toggleSelect = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((item) => item !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleBulkAction = async (action: string) => {
    if (selectedIds.length === 0) return;
    try {
      setLoading(true);
      await api.bulkAction(selectedIds, action);
      setSelectedIds([]);
      await fetchLeads();
    } catch (err: any) {
      alert(err.response?.data?.detail || `Failed to execute bulk ${action}`);
    } finally {
      setLoading(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await api.approveLead(id);
      await fetchLeads();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Approval failed. Only Reviewer or Admin can approve.');
    }
  };

  const handleReject = async (id: string) => {
    try {
      await api.rejectLead(id);
      await fetchLeads();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Rejection failed.');
    }
  };

  const handleVerify = async (id: string) => {
    try {
      await api.verifyLeads({ lead_id: id });
      await fetchLeads();
    } catch (err: any) {
      alert('Verification failed');
    }
  };

  const handleClassify = async (id: string) => {
    try {
      await api.classifyLeads({ lead_id: id });
      await fetchLeads();
    } catch (err: any) {
      alert('RAG classification failed');
    }
  };

  const handleSuppress = async (email: string) => {
    const confirmSuppress = window.confirm(`Permanently add ${email} to the global suppression list?`);
    if (!confirmSuppress) return;
    try {
      await api.addSuppression({ email, reason: 'manual_lead_table' });
      await fetchLeads();
    } catch (err) {
      alert('Suppression failed');
    }
  };

  const handleDeleteByEmail = async (email: string) => {
    const confirmDelete = window.confirm(`GDPR Art. 17 Data Erasure: Permanently delete lead records for ${email}?`);
    if (!confirmDelete) return;
    try {
      await api.deleteLeadByEmail(email);
      await fetchLeads();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Deletion failed. Requires Admin role.');
    }
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Lead Intelligence Directory</h1>
          <p className="text-sm text-slate-500 mt-1">
            Searchable registry of prospects with email deliverability status, RAG sector tagging, and approval controls.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchLeads}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <a
            href={api.getExportCsvUrl()}
            target="_blank"
            rel="noreferrer"
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 shadow-sm"
          >
            <Download className="w-3.5 h-3.5 text-slate-500" />
            Export CSV
          </a>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs flex flex-wrap items-center gap-4 text-xs">
        {/* Company / Domain / Email Search Field */}
        <div className="relative flex-1 min-w-[260px] max-w-sm">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search company name, domain, or email..."
            value={localSearch}
            onChange={(e) => setLocalSearch(e.target.value)}
            className="w-full pl-9 pr-8 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:bg-white transition"
          />
          {localSearch && (
            <button
              onClick={() => setLocalSearch('')}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-0.5"
              title="Clear search"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        <div className="flex items-center gap-1.5 text-slate-500 font-semibold uppercase tracking-wider text-[11px]">
          <Filter className="w-3.5 h-3.5" /> Filters:
        </div>

        <div>
          <select
            value={sectorFilter}
            onChange={(e) => setSectorFilter(e.target.value)}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-700"
          >
            <option value="All">All Sectors</option>
            <option value="Information Technology">Information Technology</option>
            <option value="Financial Services">Financial Services</option>
            <option value="Healthcare & Life Sciences">Healthcare & Life Sciences</option>
            <option value="Manufacturing & Industrial">Manufacturing & Industrial</option>
            <option value="Retail & E-Commerce">Retail & E-Commerce</option>
            <option value="Professional & Legal Services">Professional & Legal Services</option>
            <option value="CleanTech & Energy">CleanTech & Energy</option>
          </select>
        </div>

        <div>
          <select
            value={regionFilter}
            onChange={(e) => setRegionFilter(e.target.value)}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-700"
          >
            <option value="All">All Regions</option>
            <option value="North America">North America</option>
            <option value="Europe (UK/EU)">Europe (UK/EU)</option>
            <option value="Asia-Pacific">Asia-Pacific</option>
          </select>
        </div>

        <div>
          <select
            value={verificationFilter}
            onChange={(e) => setVerificationFilter(e.target.value)}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-700"
          >
            <option value="All">All Email Statuses</option>
            <option value="valid">Valid (Verified MX)</option>
            <option value="risky">Risky (Freemail / Role-based)</option>
            <option value="invalid">Invalid (No MX / Bad Syntax)</option>
            <option value="unknown">Unknown (Unverified)</option>
          </select>
        </div>

        <div>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-md text-slate-700"
          >
            <option value="All">All Pipeline Statuses</option>
            <option value="new">New</option>
            <option value="verified">Verified</option>
            <option value="approved">Approved</option>
            <option value="contacted">Contacted</option>
            <option value="replied">Replied</option>
            <option value="bounced">Bounced</option>
            <option value="suppressed">Suppressed</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>

        <div className="ml-auto text-slate-400 font-medium">
          Showing <span className="text-slate-800 font-bold">{leads.length}</span> records
        </div>
      </div>

      {/* Bulk Action Floating Toolbar */}
      {selectedIds.length > 0 && (
        <div className="bg-slate-900 text-white px-5 py-3 rounded-xl shadow-lg flex items-center justify-between text-xs animate-in fade-in">
          <div className="font-semibold flex items-center gap-2">
            <span>{selectedIds.length} leads selected</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleBulkAction('verify')}
              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 rounded-lg font-medium transition"
            >
              Verify Emails
            </button>
            <button
              onClick={() => handleBulkAction('approve')}
              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 rounded-lg font-medium transition"
            >
              Bulk Approve
            </button>
            <button
              onClick={() => handleBulkAction('reject')}
              className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg font-medium transition"
            >
              Bulk Reject
            </button>
            {currentRole === 'admin' && (
              <button
                onClick={() => handleBulkAction('delete')}
                className="px-3 py-1.5 bg-rose-600 hover:bg-rose-700 rounded-lg font-medium transition"
              >
                Delete Selected
              </button>
            )}
          </div>
        </div>
      )}

      {/* Leads Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50/70 border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              <tr>
                <th className="px-4 py-3.5 w-10">
                  <button onClick={handleSelectAll} className="text-slate-500 hover:text-slate-900">
                    {selectedIds.length > 0 && selectedIds.length === leads.length ? (
                      <CheckSquare className="w-4 h-4 text-blue-600" />
                    ) : (
                      <Square className="w-4 h-4 text-slate-300" />
                    )}
                  </button>
                </th>
                <th className="px-4 py-3.5">Company & Contact</th>
                <th className="px-4 py-3.5">Email & Verification</th>
                <th className="px-4 py-3.5">Sector (RAG)</th>
                <th className="px-4 py-3.5">Region</th>
                <th className="px-4 py-3.5">Pipeline Status</th>
                <th className="px-4 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {leads.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-5 py-12 text-center text-slate-400">
                    No leads found matching current filters.
                  </td>
                </tr>
              ) : (
                leads.map((lead) => {
                  const isSelected = selectedIds.includes(lead.id);
                  return (
                    <tr key={lead.id} className={`hover:bg-slate-50/60 transition ${isSelected ? 'bg-blue-50/40' : ''}`}>
                      <td className="px-4 py-3.5">
                        <button onClick={() => toggleSelect(lead.id)}>
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4 text-blue-600" />
                          ) : (
                            <Square className="w-4 h-4 text-slate-300" />
                          )}
                        </button>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="font-semibold text-slate-900">{lead.company?.name || 'Company Profile'}</div>
                        <div className="text-[11px] text-slate-500 mt-0.5">
                          {lead.name} {lead.title ? `&bull; ${lead.title}` : ''}
                        </div>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="font-mono text-slate-800 font-medium">{lead.email}</div>
                        <div className="mt-1 flex items-center gap-1.5">
                          <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold ${
                            lead.email_status === 'valid' ? 'bg-emerald-100 text-emerald-800' :
                            lead.email_status === 'risky' ? 'bg-amber-100 text-amber-800' :
                            lead.email_status === 'invalid' ? 'bg-rose-100 text-rose-800' :
                            'bg-slate-100 text-slate-600'
                          }`}>
                            {lead.email_status.toUpperCase()}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="font-semibold text-slate-800">{lead.sector || 'Unassigned'}</div>
                        <div className="text-[10px] text-slate-400 flex items-center gap-1 mt-0.5">
                          <span>Conf:</span>
                          <span className={`font-mono font-bold ${lead.sector_confidence >= 0.85 ? 'text-emerald-600' : 'text-amber-600'}`}>
                            {(lead.sector_confidence * 100).toFixed(0)}%
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-slate-600">{lead.region || 'North America'}</td>
                      <td className="px-4 py-3.5">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                          lead.status === 'approved' ? 'bg-indigo-100 text-indigo-800' :
                          lead.status === 'verified' ? 'bg-blue-100 text-blue-800' :
                          lead.status === 'contacted' ? 'bg-teal-100 text-teal-800' :
                          lead.status === 'suppressed' ? 'bg-slate-200 text-slate-700' :
                          lead.status === 'rejected' ? 'bg-rose-100 text-rose-800' :
                          'bg-amber-100 text-amber-800'
                        }`}>
                          {lead.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right space-x-1">
                        <button
                          onClick={() => setSelectedLead(lead)}
                          title="View Lead Details"
                          className="p-1 rounded text-slate-500 hover:text-slate-800 hover:bg-slate-100"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleVerify(lead.id)}
                          title="Verify Email Address"
                          className="p-1 rounded text-blue-600 hover:bg-blue-50"
                        >
                          <ShieldCheck className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleClassify(lead.id)}
                          title="Classify with RAG Agent"
                          className="p-1 rounded text-purple-600 hover:bg-purple-50"
                        >
                          <Cpu className="w-3.5 h-3.5" />
                        </button>
                        {(currentRole === 'admin' || currentRole === 'reviewer') && (
                          <>
                            <button
                              onClick={() => handleApprove(lead.id)}
                              title="Approve for Campaigns"
                              className="p-1 rounded text-emerald-600 hover:bg-emerald-50"
                            >
                              <CheckCircle2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              onClick={() => handleReject(lead.id)}
                              title="Reject Lead"
                              className="p-1 rounded text-rose-600 hover:bg-rose-50"
                            >
                              <XCircle className="w-3.5 h-3.5" />
                            </button>
                          </>
                        )}
                        <button
                          onClick={() => handleSuppress(lead.email)}
                          title="Add to Global Suppression"
                          className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100"
                        >
                          <Ban className="w-3.5 h-3.5" />
                        </button>
                        {currentRole === 'admin' && (
                          <button
                            onClick={() => handleDeleteByEmail(lead.email)}
                            title="GDPR Right to Erasure"
                            className="p-1 rounded text-rose-500 hover:bg-rose-50"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Lead Details Modal */}
      {selectedLead && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-lg w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Lead Dossier & Compliance Trace</h3>
              <button onClick={() => setSelectedLead(null)} className="text-slate-400 hover:text-slate-700 text-lg font-bold">
                &times;
              </button>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <span className="text-slate-400 block mb-0.5">Contact</span>
                <div className="font-semibold text-slate-900 text-sm">
                  {selectedLead.name} &bull; {selectedLead.title || 'Executive'}
                </div>
                <div className="font-mono text-blue-600">{selectedLead.email}</div>
              </div>

              <div>
                <span className="text-slate-400 block mb-0.5">Company</span>
                <div className="font-semibold text-slate-800">{selectedLead.company?.name}</div>
                <a href={selectedLead.company?.website} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline">
                  {selectedLead.company?.website || 'N/A'}
                </a>
                <p className="text-slate-600 mt-1">{selectedLead.company?.description}</p>
              </div>

              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-100">
                <div>
                  <span className="text-slate-400 block">Sector Classification</span>
                  <div className="font-semibold text-slate-800">{selectedLead.sector}</div>
                  <div className="text-[11px] text-slate-500">{selectedLead.sector_reason}</div>
                </div>
                <div>
                  <span className="text-slate-400 block">Verification Status</span>
                  <span className="inline-block mt-0.5 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                    {selectedLead.email_status.toUpperCase()}
                  </span>
                </div>
              </div>

              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1">
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Lawful Basis Documentation</span>
                <p className="text-slate-700 text-[11px]">{selectedLead.lawful_basis_note}</p>
                <div className="text-[10px] text-slate-400 font-mono">
                  Source: {selectedLead.source_type} &bull; Collected: {new Date(selectedLead.collected_at).toLocaleDateString()}
                </div>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedLead(null)}
                className="px-4 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-800"
              >
                Close Dossier
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

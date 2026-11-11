import React, { useState, useEffect } from 'react';
import { Cpu, CheckCircle2, AlertCircle, RefreshCw, Play, Layers, Sparkles } from 'lucide-react';
import { api } from '../services/api';
import { Lead } from '../types';

export const Segmentation: React.FC = () => {
  const [leads, setLeads] = useState<Lead[]>([]);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const fetchLeads = async () => {
    try {
      setLoading(true);
      const data = await api.listLeads();
      setLeads(data);
    } catch (err) {
      console.error('Failed to load leads for segmentation:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, []);

  const handleRunClassification = async () => {
    try {
      setLoading(true);
      const res = await api.classifyLeads({ classify_all_unclassified: true });
      setFeedback(res.message);
      await fetchLeads();
    } catch (err) {
      alert('Classification run failed');
    } finally {
      setLoading(false);
    }
  };

  const needsReviewLeads = leads.filter(
    (l) => l.sector_confidence < 0.75 || l.sector === 'Needs Review' || !l.sector
  );

  const highConfidenceLeads = leads.filter(
    (l) => l.sector_confidence >= 0.75 && l.sector !== 'Needs Review' && l.sector
  );

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">RAG Sector Classification & Segmentation</h1>
          <p className="text-sm text-slate-500 mt-1">
            Integration with RAG Lead Segregation Agent for deep industry taxonomy classification and human review.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRunClassification}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-xs font-semibold rounded-lg shadow-sm transition disabled:opacity-50"
          >
            <Cpu className="w-4 h-4" />
            {loading ? 'Classifying via RAG Engine...' : 'Run RAG Sector Classification'}
          </button>
        </div>
      </div>

      {/* RAG Agent Status Banner */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-slate-500">RAG Agent Connection</span>
            <div className="text-base font-bold text-slate-900 mt-1 flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
              Active Engine
            </div>
            <div className="text-[11px] text-slate-400 mt-0.5">POST /api/leads/classify</div>
          </div>
          <div className="w-10 h-10 rounded-lg bg-purple-50 text-purple-600 flex items-center justify-center font-bold">
            <Cpu className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-slate-500">High-Confidence Classified</span>
            <div className="text-2xl font-bold text-emerald-600 mt-1">{highConfidenceLeads.length}</div>
            <div className="text-[11px] text-slate-400 mt-0.5">&ge; 75% match threshold</div>
          </div>
          <div className="w-10 h-10 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center font-bold">
            <CheckCircle2 className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs flex items-center justify-between">
          <div>
            <span className="text-xs font-medium text-slate-500">Needs Human Review</span>
            <div className="text-2xl font-bold text-amber-600 mt-1">{needsReviewLeads.length}</div>
            <div className="text-[11px] text-slate-400 mt-0.5">Held back from campaigns</div>
          </div>
          <div className="w-10 h-10 rounded-lg bg-amber-50 text-amber-600 flex items-center justify-center font-bold">
            <AlertCircle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {feedback && (
        <div className="p-4 bg-purple-50 border border-purple-200 rounded-xl text-xs text-purple-900 flex items-center justify-between">
          <span>{feedback}</span>
          <button onClick={() => setFeedback(null)} className="text-purple-700 font-bold">&times;</button>
        </div>
      )}

      {/* Needs Review Priority Queue */}
      <div className="bg-white rounded-xl border border-amber-200/80 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-amber-100 bg-amber-50/40 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-amber-950 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-amber-600" />
              Needs Review Queue (Uncertain Classifications)
            </h2>
            <p className="text-xs text-amber-800/80 mt-0.5">
              These leads remain excluded from campaigns until a reviewer verifies their sector.
            </p>
          </div>
          <span className="px-2.5 py-1 bg-amber-100 text-amber-800 rounded-full text-xs font-bold">
            {needsReviewLeads.length} in Review
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50/70 border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              <tr>
                <th className="px-5 py-3">Company & Contact</th>
                <th className="px-5 py-3">Website & Domain</th>
                <th className="px-5 py-3">Proposed Sector</th>
                <th className="px-5 py-3">Confidence</th>
                <th className="px-5 py-3">RAG Agent Rationale</th>
                <th className="px-5 py-3 text-right">Human Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {needsReviewLeads.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-400">
                    All current leads meet high-confidence classification criteria (&ge; 75%).
                  </td>
                </tr>
              ) : (
                needsReviewLeads.map((lead) => (
                  <tr key={lead.id} className="hover:bg-slate-50/50">
                    <td className="px-5 py-3.5">
                      <div className="font-semibold text-slate-900">{lead.company?.name || lead.name}</div>
                      <div className="text-[11px] text-slate-400">{lead.title || 'Executive'}</div>
                    </td>
                    <td className="px-5 py-3.5 text-blue-600 font-mono text-[11px]">
                      {lead.company?.website || lead.email.split('@')[1]}
                    </td>
                    <td className="px-5 py-3.5 font-semibold text-slate-800">
                      {lead.sector || 'Unclassified'}
                    </td>
                    <td className="px-5 py-3.5 font-bold font-mono text-amber-600">
                      {(lead.sector_confidence * 100).toFixed(0)}%
                    </td>
                    <td className="px-5 py-3.5 text-slate-500 text-[11px]">
                      {lead.sector_reason || 'Pending analysis'}
                    </td>
                    <td className="px-5 py-3.5 text-right">
                      <button
                        onClick={() => api.approveLead(lead.id).then(fetchLeads)}
                        className="px-3 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-medium text-[11px]"
                      >
                        Confirm Sector
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* High-Confidence Classifications Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Verified Sector Classifications</h2>
            <p className="text-xs text-slate-500">Autonomous taxonomy classifications with high confidence</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50/70 border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              <tr>
                <th className="px-5 py-3">Company</th>
                <th className="px-5 py-3">Assigned Sector</th>
                <th className="px-5 py-3">Confidence</th>
                <th className="px-5 py-3">Classification Rationale</th>
                <th className="px-5 py-3">Source Engine</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {highConfidenceLeads.map((lead) => (
                <tr key={lead.id} className="hover:bg-slate-50/50">
                  <td className="px-5 py-3 font-semibold text-slate-900">{lead.company?.name || lead.name}</td>
                  <td className="px-5 py-3">
                    <span className="px-2 py-0.5 rounded font-bold text-[10px] bg-purple-100 text-purple-800">
                      {lead.sector}
                    </span>
                  </td>
                  <td className="px-5 py-3 font-mono font-bold text-emerald-600">
                    {(lead.sector_confidence * 100).toFixed(0)}%
                  </td>
                  <td className="px-5 py-3 text-slate-600 text-[11px]">{lead.sector_reason}</td>
                  <td className="px-5 py-3 text-slate-400 font-mono text-[10px] uppercase">
                    RAG Segregation Agent
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

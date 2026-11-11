import React, { useState, useEffect } from 'react';
import { 
  Send, Plus, Eye, CheckCircle2, Pause, Play, AlertTriangle, 
  Layers, Clock, ShieldAlert, Sparkles, RefreshCw, UserCheck 
} from 'lucide-react';
import { api } from '../services/api';
import { Campaign, UserRole, CampaignStep } from '../types';

interface CampaignsProps {
  currentRole: UserRole;
}

export const Campaigns: React.FC<CampaignsProps> = ({ currentRole }) => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [previewData, setPreviewData] = useState<any | null>(null);
  const [sendFeedback, setSendFeedback] = useState<any | null>(null);

  // New Campaign Form
  const [name, setName] = useState('');
  const [targetSector, setTargetSector] = useState('Information Technology');
  const [targetRegion, setTargetRegion] = useState('North America');
  const [dailyLimit, setDailyLimit] = useState(50);
  const [subject, setSubject] = useState('Improving compute architecture for {{company}}');
  const [body, setBody] = useState(
    'Hi {{first_name}},\n\nI noticed {{company}}\'s leadership in the {{sector}} sector. Engineering teams often struggle with container cost opacity.\n\nOur telemetry engine automated 28% efficiency gains for similar infrastructure. Would you have 10 minutes next Tuesday to review a tailored benchmark?\n\nBest regards,\nDevin Cole\nLead Shark Outreach Team'
  );

  // Sequence follow-ups
  const [enableFollowUps, setEnableFollowUps] = useState(true);
  const [followUp1Days, setFollowUp1Days] = useState(3);
  const [followUp1Body, setFollowUp1Body] = useState(
    'Hi {{first_name}},\n\nFollowing up on my note below regarding {{company}}\'s cloud telemetry. Let me know if you would like me to send over our one-page technical architecture doc.\n\nBest,\nDevin'
  );

  const fetchCampaigns = async () => {
    try {
      setLoading(true);
      const data = await api.listCampaigns();
      setCampaigns(data);
    } catch (err) {
      console.error('Failed to load campaigns:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCampaigns();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setLoading(true);
      const steps: CampaignStep[] = [
        { step_no: 1, delay_days: 0, subject, body }
      ];
      if (enableFollowUps) {
        steps.push({
          step_no: 2,
          delay_days: followUp1Days,
          subject: `Re: ${subject}`,
          body: followUp1Body
        });
      }

      await api.createCampaign({
        name,
        target_sector: targetSector,
        target_region: targetRegion,
        daily_limit: dailyLimit,
        subject,
        body,
        steps
      });

      setShowCreateModal(false);
      setName('');
      await fetchCampaigns();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to create campaign');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitForApproval = async (id: string) => {
    try {
      await api.submitForApproval(id);
      await fetchCampaigns();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to submit for approval');
    }
  };

  const handleApprove = async (id: string) => {
    try {
      await api.approveCampaign(id);
      await fetchCampaigns();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Approval failed. The campaign creator cannot approve their own campaign.');
    }
  };

  const handlePauseResume = async (camp: Campaign) => {
    try {
      if (camp.status === 'paused') {
        await api.resumeCampaign(camp.id);
      } else {
        await api.pauseCampaign(camp.id);
      }
      await fetchCampaigns();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Action failed');
    }
  };

  const handlePreview = async (id: string) => {
    try {
      const data = await api.previewCampaign(id);
      setPreviewData(data);
    } catch (err: any) {
      alert('Failed to generate preview');
    }
  };

  const handleSendBatch = async (id: string) => {
    try {
      setLoading(true);
      const res = await api.sendCampaignBatch(id, 3);
      setSendFeedback(res);
      await fetchCampaigns();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Cannot send: Pre-Send Compliance checks failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Outreach Campaign Management</h1>
          <p className="text-sm text-slate-500 mt-1">
            Compliant sequence builder with merge personalization, mandatory human approval, and auto-pause safeguards.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchCampaigns}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm transition"
          >
            <Plus className="w-3.5 h-3.5" />
            Create Campaign
          </button>
        </div>
      </div>

      {/* Mandatory Human Approval Policy Callout */}
      <div className="p-4 rounded-xl bg-purple-50/70 border border-purple-200/80 flex items-start gap-3">
        <UserCheck className="w-5 h-5 text-purple-600 shrink-0 mt-0.5" />
        <div className="text-xs text-purple-900 leading-relaxed">
          <span className="font-bold">Separation of Duties & Mandatory Human Approval: </span>
          Drafted campaigns can never dispatch emails without Reviewer approval. The campaign creator cannot approve their own campaign. Any edit to template text immediately resets approval state to Draft.
        </div>
      </div>

      {sendFeedback && (
        <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-950 space-y-2">
          <div className="flex items-center justify-between font-bold text-sm text-emerald-900">
            <span>Simulated Outbound Batch Sent Successfully</span>
            <button onClick={() => setSendFeedback(null)}>&times;</button>
          </div>
          <div className="text-xs text-emerald-800">
            {sendFeedback.sent_count} emails simulated via Safe Virtual Outbound Queue. 
            ({sendFeedback.failed_count} skipped/blocked by Pre-Send Checklist).
          </div>
          <div className="space-y-1 pt-1">
            {sendFeedback.results?.map((r: any, idx: number) => (
              <div key={idx} className="font-mono text-[11px] text-emerald-700">
                &bull; {r.email}: {r.detail}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Campaigns Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Campaign Directory</h2>
            <p className="text-xs text-slate-500">Scheduled sequence pipelines and approval workflows</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50/70 border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              <tr>
                <th className="px-5 py-3.5">Campaign Name</th>
                <th className="px-5 py-3.5">Target Sector & Region</th>
                <th className="px-5 py-3.5">Workflow Status</th>
                <th className="px-5 py-3.5">Daily Cap</th>
                <th className="px-5 py-3.5">Sends Recorded</th>
                <th className="px-5 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {campaigns.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-5 py-10 text-center text-slate-400">
                    No campaigns created yet. Click "Create Campaign" to launch a compliant sequence.
                  </td>
                </tr>
              ) : (
                campaigns.map((camp) => (
                  <tr key={camp.id} className="hover:bg-slate-50/50 transition">
                    <td className="px-5 py-3.5">
                      <div className="font-semibold text-slate-900">{camp.name}</div>
                      <div className="text-[11px] text-slate-400 font-mono mt-0.5">Subject: {camp.subject}</div>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className="font-semibold text-slate-800">{camp.target_sector}</span>
                      <div className="text-[11px] text-slate-400">{camp.target_region || 'Global'}</div>
                    </td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                        camp.status === 'approved' ? 'bg-indigo-100 text-indigo-800' :
                        camp.status === 'sending' ? 'bg-emerald-100 text-emerald-800 animate-pulse' :
                        camp.status === 'pending_approval' ? 'bg-amber-100 text-amber-800' :
                        camp.status === 'paused' ? 'bg-rose-100 text-rose-800' :
                        'bg-slate-100 text-slate-600'
                      }`}>
                        {camp.status.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 font-bold text-slate-700">{camp.daily_limit}/day</td>
                    <td className="px-5 py-3.5 font-bold text-blue-600">{camp.total_sends}</td>
                    <td className="px-5 py-3.5 text-right space-x-1.5">
                      <button
                        onClick={() => handlePreview(camp.id)}
                        className="px-2.5 py-1 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded font-medium text-[11px] transition"
                      >
                        Preview
                      </button>

                      {camp.status === 'draft' && (
                        <button
                          onClick={() => handleSubmitForApproval(camp.id)}
                          className="px-2.5 py-1 bg-amber-500 hover:bg-amber-600 text-white rounded font-medium text-[11px] transition"
                        >
                          Submit Review
                        </button>
                      )}

                      {(camp.status === 'pending_approval' || camp.status === 'draft') && 
                       (currentRole === 'admin' || currentRole === 'reviewer') && (
                        <button
                          onClick={() => handleApprove(camp.id)}
                          className="px-2.5 py-1 bg-emerald-600 hover:bg-emerald-700 text-white rounded font-medium text-[11px] transition"
                        >
                          Approve
                        </button>
                      )}

                      {(camp.status === 'approved' || camp.status === 'sending' || camp.status === 'paused') && (
                        <>
                          <button
                            onClick={() => handleSendBatch(camp.id)}
                            className="px-2.5 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-medium text-[11px] transition"
                          >
                            Simulate Send
                          </button>
                          <button
                            onClick={() => handlePauseResume(camp)}
                            className="px-2.5 py-1 bg-slate-700 hover:bg-slate-800 text-white rounded font-medium text-[11px] transition"
                          >
                            {camp.status === 'paused' ? 'Resume' : 'Pause'}
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Campaign Creation Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-2xl w-full p-6 space-y-5 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Create Compliant Outreach Campaign</h3>
              <button onClick={() => setShowCreateModal(false)} className="text-slate-400 hover:text-slate-700 text-lg font-bold">
                &times;
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">Campaign Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Q4 Cloud Telemetry Outreach"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Target Sector</label>
                  <select
                    value={targetSector}
                    onChange={(e) => setTargetSector(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                  >
                    <option value="Information Technology">Information Technology</option>
                    <option value="Financial Services">Financial Services</option>
                    <option value="Healthcare & Life Sciences">Healthcare & Life Sciences</option>
                    <option value="Manufacturing & Industrial">Manufacturing & Industrial</option>
                    <option value="Retail & E-Commerce">Retail & E-Commerce</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Target Region</label>
                  <select
                    value={targetRegion}
                    onChange={(e) => setTargetRegion(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                  >
                    <option value="North America">North America</option>
                    <option value="Europe (UK/EU)">Europe (UK/EU)</option>
                    <option value="Global">Global</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Daily Cap (Emails/Day)</label>
                  <input
                    type="number"
                    min="5"
                    max="500"
                    value={dailyLimit}
                    onChange={(e) => setDailyLimit(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="font-semibold text-slate-700">Initial Email Subject</label>
                  <span className="text-[10px] text-slate-400">Merge tags: <code>{"{{company}}"}</code></span>
                </div>
                <input
                  type="text"
                  required
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800"
                />
              </div>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="font-semibold text-slate-700">Initial Email Body</label>
                  <span className="text-[10px] text-slate-400">
                    Supported: <code>{"{{first_name}}"}</code>, <code>{"{{company}}"}</code>, <code>{"{{sector}}"}</code>
                  </span>
                </div>
                <textarea
                  rows={5}
                  required
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-sans"
                />
              </div>

              {/* Automated Sequence Follow-up */}
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-slate-800">Sequence Step 2 (Follow-up)</span>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableFollowUps}
                      onChange={(e) => setEnableFollowUps(e.target.checked)}
                      className="rounded text-blue-600"
                    />
                    <span className="text-[11px] text-slate-600 font-medium">Enable Step 2</span>
                  </label>
                </div>

                {enableFollowUps && (
                  <div className="space-y-2 pt-1">
                    <div className="flex items-center gap-2">
                      <span className="text-slate-500">Wait Delay:</span>
                      <input
                        type="number"
                        min="1"
                        max="14"
                        value={followUp1Days}
                        onChange={(e) => setFollowUp1Days(Number(e.target.value))}
                        className="w-16 px-2 py-1 bg-white border border-slate-200 rounded text-center font-bold"
                      />
                      <span className="text-slate-500">days after Step 1 without reply</span>
                    </div>
                    <textarea
                      rows={3}
                      value={followUp1Body}
                      onChange={(e) => setFollowUp1Body(e.target.value)}
                      className="w-full px-2.5 py-1.5 bg-white border border-slate-200 rounded text-slate-800 font-sans"
                    />
                  </div>
                )}
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 border border-slate-200 rounded-lg text-slate-700 hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg shadow-sm"
                >
                  Create Campaign (Draft)
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Preview Modal */}
      {previewData && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-xl w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-base font-bold text-slate-900">Email Preview (Rendered With Merge Fields)</h3>
              <button onClick={() => setPreviewData(null)} className="text-slate-400 hover:text-slate-700 text-lg font-bold">
                &times;
              </button>
            </div>

            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs space-y-1">
              <div><span className="text-slate-400">From: </span><span className="font-semibold text-slate-800">{previewData.sender_info?.from_name} &lt;{previewData.sender_info?.from_address}&gt;</span></div>
              <div><span className="text-slate-400">To Sample: </span><span className="font-semibold text-slate-800">{previewData.sample_lead?.name} &lt;{previewData.sample_lead?.email}&gt;</span></div>
              <div><span className="text-slate-400">Subject: </span><span className="font-bold text-blue-600">{previewData.rendered_subject}</span></div>
            </div>

            {/* Rendered HTML Body */}
            <div 
              className="border border-slate-200 rounded-lg p-4 bg-white text-xs max-h-72 overflow-y-auto"
              dangerouslySetInnerHTML={{ __html: previewData.rendered_body_html }}
            />

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setPreviewData(null)}
                className="px-4 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-semibold"
              >
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

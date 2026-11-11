import React, { useState, useEffect } from 'react';
import { 
  Compass, Upload, ShieldCheck, CheckCircle2, AlertCircle, 
  RefreshCw, Play, FileSpreadsheet, Globe, MapPin, Sparkles, Filter 
} from 'lucide-react';
import { api } from '../services/api';
import { DiscoveryJob } from '../types';

interface LeadDiscoveryProps {
  onNavigateToLeads: () => void;
}

export const LeadDiscovery: React.FC<LeadDiscoveryProps> = ({ onNavigateToLeads }) => {
  const [jobs, setJobs] = useState<DiscoveryJob[]>([]);
  const [loading, setLoading] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  // Form state
  const [jobName, setJobName] = useState('');
  const [query, setQuery] = useState('');
  const [industry, setIndustry] = useState('Information Technology');
  const [region, setRegion] = useState('North America');
  const [source, setSource] = useState('demo');
  const [maxResults, setMaxResults] = useState(25);

  const fetchJobs = async () => {
    try {
      setLoading(true);
      const data = await api.listDiscoveryJobs();
      setJobs(data);
    } catch (err) {
      console.error('Error fetching jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jobName || !query) {
      alert('Please provide a Job Name and Search Query');
      return;
    }

    try {
      setLoading(true);
      await api.createDiscoveryJob({
        job_name: jobName,
        source,
        query,
        region,
        max_results: Number(maxResults),
        schedule: 'once',
      });
      // Reset form
      setJobName('');
      setQuery('');
      await fetchJobs();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to execute discovery job');
    } finally {
      setLoading(false);
    }
  };

  const handleCsvUpload = async () => {
    if (!csvFile) return;
    try {
      setLoading(true);
      setUploadStatus('Importing and deduplicating CSV records...');
      const res = await api.importLeadsCsv(csvFile);
      setUploadStatus(res.message);
      setCsvFile(null);
      await fetchJobs();
    } catch (err: any) {
      setUploadStatus(err.response?.data?.detail || 'Failed to import CSV');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Lead Discovery Module</h1>
          <p className="text-sm text-slate-500 mt-1">
            Discover business prospects from lawful public listings, permitted map APIs, and verified CSV imports.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchJobs}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 shadow-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={onNavigateToLeads}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm"
          >
            View All Discovered Leads &rarr;
          </button>
        </div>
      </div>

      {/* Compliance Safety Notice Banner */}
      <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200/80 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
        <div className="text-xs text-blue-900 leading-relaxed">
          <span className="font-bold">Lawful Sourcing & Robots.txt Strict Enforcement: </span>
          Lead Shark only extracts business contact information listed publicly for commercial inquiries. It strictly obeys <code className="bg-blue-100 px-1 py-0.5 rounded text-blue-800">robots.txt</code>, does not scrape private or login-protected data (such as LinkedIn), and never solves or evades CAPTCHAs.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Discovery Form */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-6">
          <div className="flex items-center gap-2 pb-4 border-b border-slate-100">
            <Compass className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-semibold text-slate-900">Configure Discovery Job</h2>
          </div>

          <form onSubmit={handleCreateJob} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Job Name</label>
                <input
                  type="text"
                  placeholder="e.g. Q4 Cloud Infra Prospects"
                  value={jobName}
                  onChange={(e) => setJobName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Source Selection</label>
                <select
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                >
                  <option value="demo">Demo Discovery Connector (Safely Labeled Sample Data)</option>
                  <option value="osm">OpenStreetMap / Permitted Public Map Directory</option>
                  <option value="google_places">Google Places API (Requires API Key)</option>
                  <option value="website">Company Website (robots.txt checked)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="sm:col-span-2">
                <label className="block text-xs font-semibold text-slate-700 mb-1">Business Search Query</label>
                <input
                  type="text"
                  placeholder="e.g. Kubernetes, DevOps, or Robotics"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Target Region</label>
                <select
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                >
                  <option value="North America">North America</option>
                  <option value="Europe (UK/EU)">Europe (UK/EU)</option>
                  <option value="Asia-Pacific">Asia-Pacific</option>
                  <option value="Global">Global</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Industry Focus</label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                >
                  <option value="Information Technology">Information Technology</option>
                  <option value="Manufacturing & Industrial">Manufacturing & Industrial</option>
                  <option value="Healthcare & Life Sciences">Healthcare & Life Sciences</option>
                  <option value="Financial Services">Financial Services</option>
                  <option value="Retail & E-Commerce">Retail & E-Commerce</option>
                  <option value="Professional & Legal Services">Professional & Legal Services</option>
                  <option value="CleanTech & Energy">CleanTech & Energy</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Max Results</label>
                <input
                  type="number"
                  min="5"
                  max="200"
                  value={maxResults}
                  onChange={(e) => setMaxResults(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-lg shadow-sm flex items-center justify-center gap-2 transition disabled:opacity-50"
              >
                <Play className="w-4 h-4 fill-white" />
                {loading ? 'Executing Discovery...' : 'Execute Lawful Discovery Job'}
              </button>
            </div>
          </form>
        </div>

        {/* Right Column: CSV Upload & Guidelines */}
        <div className="space-y-6">
          {/* CSV Upload Card */}
          <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
              <FileSpreadsheet className="w-5 h-5 text-emerald-600" />
              <h2 className="text-base font-semibold text-slate-900">Direct CSV Import</h2>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Upload existing sales prospect files or conference exhibitor sheets. Automatic duplicate detection and email normalization will run during ingestion.
            </p>

            <div className="border-2 border-dashed border-slate-200 rounded-lg p-5 text-center hover:bg-slate-50/60 transition cursor-pointer">
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                className="hidden"
                id="csv-file-input"
              />
              <label htmlFor="csv-file-input" className="cursor-pointer block">
                <Upload className="w-7 h-7 text-slate-400 mx-auto mb-2" />
                <span className="text-xs font-semibold text-blue-600 hover:underline">
                  {csvFile ? csvFile.name : 'Click to select CSV file'}
                </span>
                <span className="block text-[11px] text-slate-400 mt-1">
                  Required column: <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-700">email</code>
                </span>
              </label>
            </div>

            {csvFile && (
              <button
                onClick={handleCsvUpload}
                disabled={loading}
                className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-sm transition"
              >
                Upload & Deduplicate
              </button>
            )}

            {uploadStatus && (
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 text-xs font-medium text-slate-700">
                {uploadStatus}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Discovery Jobs History Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Discovery Job Execution History</h2>
            <p className="text-xs text-slate-500">Tracked source queries, duplication filters, and audit counts</p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50/70 border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              <tr>
                <th className="px-5 py-3.5">Job Name</th>
                <th className="px-5 py-3.5">Source & Query</th>
                <th className="px-5 py-3.5">Region</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Total Found</th>
                <th className="px-5 py-3.5">New Leads</th>
                <th className="px-5 py-3.5">Duplicates Filtered</th>
                <th className="px-5 py-3.5">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-5 py-8 text-center text-slate-400">
                    No discovery jobs on record. Submit the form above to trigger your first run.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-50/50 transition">
                    <td className="px-5 py-3.5 font-semibold text-slate-900">{job.job_name}</td>
                    <td className="px-5 py-3.5">
                      <span className="uppercase text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-bold mr-1.5">
                        {job.source}
                      </span>
                      <span className="text-slate-600 italic">"{job.query}"</span>
                    </td>
                    <td className="px-5 py-3.5 text-slate-600">{job.region || 'Global'}</td>
                    <td className="px-5 py-3.5">
                      <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                        job.status === 'completed' ? 'bg-emerald-100 text-emerald-800' :
                        job.status === 'running' ? 'bg-blue-100 text-blue-800 animate-pulse' :
                        'bg-rose-100 text-rose-800'
                      }`}>
                        {job.status.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 font-bold text-slate-800">{job.total_found}</td>
                    <td className="px-5 py-3.5 font-bold text-emerald-600">+{job.new_leads_count}</td>
                    <td className="px-5 py-3.5 text-slate-400">{job.duplicates_skipped}</td>
                    <td className="px-5 py-3.5 text-slate-400 font-mono text-[11px]">
                      {new Date(job.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

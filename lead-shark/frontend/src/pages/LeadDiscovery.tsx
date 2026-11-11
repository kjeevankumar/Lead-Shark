import React, { useState, useEffect, useCallback } from 'react';
import {
  Compass, Upload, ShieldCheck, CheckCircle2, AlertCircle,
  RefreshCw, Play, FileSpreadsheet, Globe, ArrowLeft,
  Eye, ExternalLink, Copy, Check, Layers, Search,
  ChevronLeft, ChevronRight, Phone, Mail, Building2, Sparkles, Database
} from 'lucide-react';
import { api } from '../services/api';
import {
  DiscoveryJob,
  DiscoveryProviderInfo,
  DiscoveryResultItem,
  DiscoveryResultsPageResponse,
} from '../types';

interface LeadDiscoveryProps {
  onNavigateToLeads: () => void;
}

const EXAMPLE_SEARCHES = [
  'Amazon',
  'Google',
  'Microsoft',
  'Wipro',
  'Infosys',
  'IT companies in Hyderabad',
  'Manufacturing companies in India',
  'Startups in Bangalore',
  'Healthcare companies in Telangana',
  'Cloud computing companies globally',
];

interface SourceOutcomeSummary {
  source_id: string;
  source_label: string;
  status: string;
  count: number;
  latency_ms: number;
  message?: string | null;
}

export const LeadDiscovery: React.FC<LeadDiscoveryProps> = ({ onNavigateToLeads }) => {
  const [jobs, setJobs] = useState<DiscoveryJob[]>([]);
  const [providers, setProviders] = useState<DiscoveryProviderInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [searching, setSearching] = useState(false);
  const [csvFile, setCsvFile] = useState<File | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);

  // Dedicated Search Results Page State
  const [activeJob, setActiveJob] = useState<DiscoveryJob | null>(null);
  const [pageData, setPageData] = useState<DiscoveryResultsPageResponse | null>(null);
  const [resultsLoading, setResultsLoading] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Results Page Filters & Pagination
  const [resPage, setResPage] = useState(1);
  const [resPageSize, setResPageSize] = useState(10);
  const [resSearch, setResSearch] = useState('');
  const [resIndustry, setResIndustry] = useState('All');
  const [resCountry, setResCountry] = useState('All');
  const [resRegion, setResRegion] = useState('All');
  const [resVerification, setResVerification] = useState('All');
  const [resStatus, setResStatus] = useState<'all' | 'new' | 'duplicate'>('all');

  // Search Form State
  const [jobName, setJobName] = useState('');
  const [query, setQuery] = useState('');
  const [industry, setIndustry] = useState('All');
  const [region, setRegion] = useState('Global');
  const [country, setCountry] = useState('');
  const [source, setSource] = useState('all');
  const [maxResults, setMaxResults] = useState(25);

  const fetchJobsAndProviders = async () => {
    try {
      setLoading(true);
      const [jobsData, provData] = await Promise.all([
        api.listDiscoveryJobs(),
        api.getDiscoveryProviders().catch(() => ({ providers: [] })),
      ]);
      setJobs(jobsData);
      if (provData?.providers) {
        setProviders(provData.providers);
      }
    } catch (err) {
      console.error('Error fetching discovery history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobsAndProviders();
  }, []);

  const fetchPagedResults = useCallback(async () => {
    if (!activeJob) return;
    try {
      setResultsLoading(true);
      const data = await api.getDiscoveryJobResultsPage(activeJob.id, {
        page: resPage,
        page_size: resPageSize,
        industry: resIndustry !== 'All' ? resIndustry : undefined,
        country: resCountry !== 'All' ? resCountry : undefined,
        region: resRegion !== 'All' ? resRegion : undefined,
        verification_status: resVerification !== 'All' ? resVerification : undefined,
        result_status: resStatus !== 'all' ? resStatus : undefined,
        search: resSearch.trim() || undefined,
      });
      setPageData(data);
      setActiveJob(data.job);
    } catch (err) {
      console.error('Failed to load paginated discovery results:', err);
    } finally {
      setResultsLoading(false);
    }
  }, [activeJob?.id, resPage, resPageSize, resIndustry, resCountry, resRegion, resVerification, resStatus, resSearch]);

  useEffect(() => {
    if (activeJob) {
      fetchPagedResults();
    }
  }, [activeJob?.id, resPage, resPageSize, resIndustry, resCountry, resRegion, resVerification, resStatus, resSearch]);

  const handleOpenJobResultsPage = (job: DiscoveryJob) => {
    setResPage(1);
    setResIndustry('All');
    setResCountry('All');
    setResRegion('All');
    setResVerification('All');
    setResStatus('all');
    setResSearch('');
    setActiveJob(job);
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleCreateJob = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      alert('Please enter any company name, industry, business category, or location');
      return;
    }

    const effectiveName = jobName.trim() || `${query.trim()} Leads Search`;

    try {
      setSearching(true);
      const createdJob = await api.createDiscoveryJob({
        job_name: effectiveName,
        source,
        query: query.trim(),
        region,
        country: country.trim() || undefined,
        industry,
        max_results: Number(maxResults),
        schedule: 'once',
      });
      setJobName('');
      await fetchJobsAndProviders();
      handleOpenJobResultsPage(createdJob);
    } catch (err: any) {
      alert(err.response?.data?.detail || err.message || 'Failed to search external sources');
    } finally {
      setSearching(false);
    }
  };

  const handleLoadDemoFallback = async (queryText: string) => {
    try {
      setSearching(true);
      const demoJob = await api.createDiscoveryJob({
        job_name: `[DEMO DATA] ${queryText}`,
        source: 'demo',
        query: queryText,
        region: 'Global',
        industry: 'All',
        max_results: 25,
        schedule: 'once',
      });
      await fetchJobsAndProviders();
      handleOpenJobResultsPage(demoJob);
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Failed to load Demo Data');
    } finally {
      setSearching(false);
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
      await fetchJobsAndProviders();
    } catch (err: any) {
      setUploadStatus(err.response?.data?.detail || 'Failed to import CSV');
    } finally {
      setLoading(false);
    }
  };

  const parseSourcesSearched = (raw?: string): SourceOutcomeSummary[] => {
    if (!raw) return [];
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  };

  const getVerificationBadge = (vstatus: string) => {
    switch (vstatus) {
      case 'verified_email':
        return { label: 'VERIFIED EMAIL', cls: 'bg-emerald-100 text-emerald-800 border-emerald-200' };
      case 'verified_domain':
        return { label: 'VERIFIED DOMAIN', cls: 'bg-blue-100 text-blue-800 border-blue-200' };
      case 'risky_email':
        return { label: 'RISKY EMAIL', cls: 'bg-amber-100 text-amber-800 border-amber-200' };
      case 'invalid_email':
        return { label: 'INVALID EMAIL', cls: 'bg-rose-100 text-rose-800 border-rose-200' };
      case 'demo_sample':
        return { label: 'DEMO SAMPLE', cls: 'bg-amber-100 text-amber-800 border-amber-300' };
      default:
        return { label: 'UNVERIFIED', cls: 'bg-slate-100 text-slate-600 border-slate-200' };
    }
  };

  // =========================================================================
  // VIEW 1: DEDICATED PER-SEARCH RESULTS PAGE
  // =========================================================================
  if (activeJob) {
    const isDemoJob = activeJob.data_mode === 'demo' || activeJob.source === 'demo';
    const sourceTelemetry = parseSourcesSearched(activeJob.sources_searched);
    const items = pageData?.items || [];
    const facets = pageData?.facets || {
      industries: [],
      countries: [],
      regions: [],
      verification_statuses: [],
      providers: [],
      result_statuses: [],
    };
    const total = pageData?.total ?? activeJob.total_found;
    const totalPages = pageData?.total_pages ?? 1;

    return (
      <div className="p-8 space-y-6 max-w-7xl mx-auto">
        {/* Top Navigation & Breadcrumb */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="space-y-1">
            <button
              onClick={() => setActiveJob(null)}
              className="inline-flex items-center gap-1.5 text-xs font-semibold text-blue-600 hover:text-blue-800 mb-1 cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to Find Business Leads &amp; Search History
            </button>
            <div className="flex flex-wrap items-center gap-2.5">
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                {activeJob.job_name}
              </h1>
              {isDemoJob ? (
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                  DEMO DATA (SYNTHETIC SAMPLE)
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-100 text-emerald-800 border border-emerald-200">
                  LIVE PUBLIC SOURCES
                </span>
              )}
              {activeJob.search_intent && (
                <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-slate-100 text-slate-700 capitalize">
                  {activeJob.search_intent.replace('_', ' ')}
                </span>
              )}
              {activeJob.cached && (
                <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-sky-100 text-sky-700">
                  Cached Result
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-4 text-xs text-slate-500 pt-1">
              <span>
                Query: <strong className="text-slate-800">"{activeJob.query}"</strong>
              </span>
              <span>
                Target Region: <strong className="text-slate-800">{activeJob.region || 'Global'}</strong>
              </span>
              {activeJob.duration_ms != null && (
                <span>
                  Latency: <strong className="text-slate-800">{(activeJob.duration_ms / 1000).toFixed(2)}s</strong>
                </span>
              )}
              <span className="flex items-center gap-1">
                Search ID:
                <code className="bg-slate-100 px-1.5 py-0.5 rounded font-mono text-[11px] text-slate-700">
                  {activeJob.id.slice(0, 12)}...
                </code>
                <button
                  onClick={() => handleCopyId(activeJob.id)}
                  className="text-slate-400 hover:text-slate-600"
                  title="Copy Full Search ID"
                >
                  {copiedId === activeJob.id ? (
                    <Check className="w-3.5 h-3.5 text-emerald-600" />
                  ) : (
                    <Copy className="w-3.5 h-3.5" />
                  )}
                </button>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              onClick={fetchPagedResults}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 shadow-sm cursor-pointer"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${resultsLoading ? 'animate-spin' : ''}`} />
              Refresh
            </button>
            <button
              onClick={onNavigateToLeads}
              className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm cursor-pointer"
            >
              View All Leads Directory &rarr;
            </button>
          </div>
        </div>

        {/* Strict Isolation Notice when viewing DEMO search */}
        {isDemoJob && (
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-300 flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-900 leading-relaxed">
              <span className="font-bold">Demo Data Mode Active: </span>
              These records are synthetic samples loaded strictly for product demonstration or testing. They are never mixed with live public business search results.
            </div>
          </div>
        )}

        {/* KPI Summary Strip + Sources Searched Telemetry */}
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs font-medium text-slate-500">Total Found</span>
            <div className="text-2xl font-bold text-slate-900 mt-1">{activeJob.total_found}</div>
            <div className="text-[11px] text-slate-400">Records retrieved &amp; persisted</div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs font-medium text-slate-500">New Added to Registry</span>
            <div className="text-2xl font-bold text-emerald-600 mt-1">+{activeJob.new_leads_count}</div>
            <div className="text-[11px] text-slate-400">Unique companies / leads saved</div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs font-medium text-slate-500">Duplicates Screened</span>
            <div className="text-2xl font-bold text-amber-600 mt-1">{activeJob.duplicates_skipped}</div>
            <div className="text-[11px] text-slate-400">Matched existing DB records</div>
          </div>
          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs">
            <span className="text-xs font-medium text-slate-500 block mb-1.5">Sources Searched</span>
            <div className="flex flex-wrap gap-1.5">
              {sourceTelemetry.length > 0 ? (
                sourceTelemetry.map((src) => (
                  <span
                    key={src.source_id}
                    title={src.message || `${src.source_label}: ${src.status}`}
                    className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-semibold border ${
                      src.status === 'ok'
                        ? 'bg-emerald-50 text-emerald-800 border-emerald-200'
                        : src.status === 'rate_limited' || src.status === 'timeout' || src.status === 'error'
                        ? 'bg-rose-50 text-rose-700 border-rose-200'
                        : 'bg-slate-50 text-slate-600 border-slate-200'
                    }`}
                  >
                    <span className="uppercase">{src.source_id}</span>
                    <span>({src.count})</span>
                  </span>
                ))
              ) : (
                <span className="text-xs text-slate-500 uppercase font-mono">{activeJob.source}</span>
              )}
            </div>
          </div>
        </div>

        {/* Zero Live Results Honest Explanation + Optional Explicit Demo Load */}
        {activeJob.total_found === 0 && !isDemoJob && (
          <div className="bg-white p-6 rounded-xl border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-6 h-6 text-amber-600 shrink-0 mt-0.5" />
              <div className="space-y-2">
                <h3 className="text-base font-bold text-slate-900">
                  {activeJob.status === 'failed'
                    ? `Search Execution Error for "${activeJob.query}"`
                    : `No Live Results Found for "${activeJob.query}"`}
                </h3>
                <p className="text-xs text-slate-600 leading-relaxed">
                  {activeJob.error_message ||
                    activeJob.no_results_reason ||
                    'Configured live public sources (Wikidata, OpenStreetMap, External Search APIs) returned 0 matching entities for this query and filter combination. Lead Shark never invents company records or synthetic emails.'}
                </p>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                onClick={() => handleLoadDemoFallback(activeJob.query)}
                disabled={searching}
                className="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white text-xs font-semibold rounded-lg shadow-sm transition cursor-pointer"
              >
                {searching ? 'Loading Demo Dataset...' : 'Load DEMO DATA for Presentation / Testing'}
              </button>
              <button
                onClick={() => setActiveJob(null)}
                className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg transition cursor-pointer"
              >
                Modify Search Query
              </button>
            </div>
          </div>
        )}

        {/* Filters Bar */}
        {activeJob.total_found > 0 && (
          <div className="bg-white p-4 rounded-xl border border-slate-200/80 shadow-xs space-y-3">
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <div className="relative flex-1 min-w-[220px]">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter results by company, domain, city, or email..."
                  value={resSearch}
                  onChange={(e) => {
                    setResSearch(e.target.value);
                    setResPage(1);
                  }}
                  className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <select
                value={resIndustry}
                onChange={(e) => {
                  setResIndustry(e.target.value);
                  setResPage(1);
                }}
                className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700"
              >
                <option value="All">All Industries ({facets.industries.length})</option>
                {facets.industries.map((ind) => (
                  <option key={ind} value={ind}>
                    {ind}
                  </option>
                ))}
              </select>

              <select
                value={resCountry}
                onChange={(e) => {
                  setResCountry(e.target.value);
                  setResPage(1);
                }}
                className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700"
              >
                <option value="All">All Countries ({facets.countries.length})</option>
                {facets.countries.map((ctry) => (
                  <option key={ctry} value={ctry}>
                    {ctry}
                  </option>
                ))}
              </select>

              <select
                value={resRegion}
                onChange={(e) => {
                  setResRegion(e.target.value);
                  setResPage(1);
                }}
                className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700"
              >
                <option value="All">All Regions</option>
                {facets.regions.map((reg) => (
                  <option key={reg} value={reg}>
                    {reg}
                  </option>
                ))}
              </select>

              <select
                value={resVerification}
                onChange={(e) => {
                  setResVerification(e.target.value);
                  setResPage(1);
                }}
                className="px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-slate-700"
              >
                <option value="All">All Verification Statuses</option>
                {facets.verification_statuses.map((vs) => (
                  <option key={vs} value={vs}>
                    {vs.replace('_', ' ').toUpperCase()}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 pt-1 border-t border-slate-100 text-xs">
              <div className="flex items-center gap-2">
                {(['all', 'new', 'duplicate'] as const).map((tab) => (
                  <button
                    key={tab}
                    onClick={() => {
                      setResStatus(tab);
                      setResPage(1);
                    }}
                    className={`px-3 py-1 rounded-lg font-semibold capitalize cursor-pointer transition ${
                      resStatus === tab
                        ? 'bg-slate-900 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {tab === 'all' ? 'All Records' : tab === 'new' ? 'New Records' : 'Duplicates'}
                  </button>
                ))}
              </div>
              <div className="text-slate-500">
                Showing <strong>{items.length}</strong> of <strong>{total}</strong> matching results
              </div>
            </div>
          </div>
        )}

        {/* Results Data Table */}
        {activeJob.total_found > 0 && (
          <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-700">
                <thead className="bg-slate-50/80 border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
                  <tr>
                    <th className="px-4 py-3.5">Company &amp; Website</th>
                    <th className="px-4 py-3.5">Category &amp; Industry</th>
                    <th className="px-4 py-3.5">Location (City &amp; Country)</th>
                    <th className="px-4 py-3.5">Public Email &amp; Phone</th>
                    <th className="px-4 py-3.5">Source &amp; Attribution</th>
                    <th className="px-4 py-3.5">Verification &amp; Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 text-xs">
                  {resultsLoading ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-12 text-center text-slate-500">
                        <RefreshCw className="w-5 h-5 animate-spin text-blue-600 mx-auto mb-2" />
                        Loading search results...
                      </td>
                    </tr>
                  ) : items.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="px-4 py-12 text-center text-slate-400">
                        No results match your active filters. Try clearing filters above.
                      </td>
                    </tr>
                  ) : (
                    items.map((res: DiscoveryResultItem) => {
                      const vBadge = getVerificationBadge(res.verification_status);
                      return (
                        <tr key={res.id} className="hover:bg-slate-50/70 transition align-top">
                          {/* Company & Website */}
                          <td className="px-4 py-3.5 max-w-[260px]">
                            <div className="flex items-center gap-1.5 flex-wrap">
                              <span className="font-bold text-slate-900">{res.company_name || 'N/A'}</span>
                              {res.is_demo && (
                                <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-100 text-amber-800 border border-amber-300">
                                  DEMO
                                </span>
                              )}
                            </div>
                            {res.website ? (
                              <a
                                href={res.website}
                                target="_blank"
                                rel="noreferrer"
                                className="text-blue-600 hover:underline font-mono text-[11px] inline-flex items-center gap-1 mt-0.5"
                              >
                                <span className="truncate max-w-[210px]">{res.website}</span>
                                <ExternalLink className="w-3 h-3 shrink-0" />
                              </a>
                            ) : (
                              <div className="text-[11px] text-slate-400 italic mt-0.5">Website not listed</div>
                            )}
                            {res.description && (
                              <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">{res.description}</p>
                            )}
                          </td>

                          {/* Business Category & Industry */}
                          <td className="px-4 py-3.5">
                            <div className="font-semibold text-slate-800">{res.industry || 'Commercial Business'}</div>
                            <div className="text-[11px] text-slate-500 mt-0.5">
                              {res.business_category || 'Business Enterprise'}
                            </div>
                          </td>

                          {/* City & Country */}
                          <td className="px-4 py-3.5">
                            <div className="font-medium text-slate-800">
                              {[res.city, res.country].filter(Boolean).join(', ') || 'Location not specified'}
                            </div>
                            <div className="text-[11px] text-slate-400 mt-0.5">{res.region || 'Global'}</div>
                          </td>

                          {/* Public Email & Phone */}
                          <td className="px-4 py-3.5 space-y-1">
                            {res.email ? (
                              <div className="flex items-center gap-1.5 font-mono text-slate-900 font-medium">
                                <Mail className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                                <span>{res.email}</span>
                              </div>
                            ) : (
                              <div className="text-[11px] text-slate-400 italic">Public email not listed</div>
                            )}
                            {res.phone ? (
                              <div className="flex items-center gap-1.5 font-mono text-slate-700 text-[11px]">
                                <Phone className="w-3 h-3 text-slate-500 shrink-0" />
                                <span>{res.phone}</span>
                              </div>
                            ) : (
                              <div className="text-[11px] text-slate-400">Phone: —</div>
                            )}
                            {res.contact_name && (
                              <div className="text-[11px] text-slate-600">Contact: {res.contact_name}</div>
                            )}
                          </td>

                          {/* Source & Provider */}
                          <td className="px-4 py-3.5 max-w-[190px]">
                            <span className="inline-block uppercase text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-semibold mb-1">
                              {res.source_provider || activeJob.source}
                            </span>
                            {res.source_url && (
                              <div>
                                <a
                                  href={res.source_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-blue-600 hover:underline text-[11px] flex items-center gap-1 truncate"
                                  title={res.source_url}
                                >
                                  <span className="truncate">{res.source_url}</span>
                                  <ExternalLink className="w-3 h-3 shrink-0" />
                                </a>
                              </div>
                            )}
                          </td>

                          {/* Verification & Result Status */}
                          <td className="px-4 py-3.5 space-y-1.5">
                            <div>
                              <span className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold border ${vBadge.cls}`}>
                                {vBadge.label}
                              </span>
                            </div>
                            <div>
                              <span
                                className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                                  res.result_status === 'new'
                                    ? 'bg-emerald-50 text-emerald-700'
                                    : res.result_status === 'duplicate'
                                    ? 'bg-amber-50 text-amber-700'
                                    : 'bg-rose-50 text-rose-700'
                                }`}
                              >
                                {res.result_status.toUpperCase()}
                              </span>
                            </div>
                            {res.duplicate_reason && (
                              <div className="text-[10px] text-amber-700 max-w-[190px]">
                                {res.duplicate_reason}
                              </div>
                            )}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination Footer */}
            <div className="px-5 py-3.5 bg-slate-50 border-t border-slate-200 flex flex-wrap items-center justify-between gap-4 text-xs">
              <div className="flex items-center gap-2 text-slate-600">
                <span>Rows per page:</span>
                <select
                  value={resPageSize}
                  onChange={(e) => {
                    setResPageSize(Number(e.target.value));
                    setResPage(1);
                  }}
                  className="px-2 py-1 bg-white border border-slate-200 rounded text-xs"
                >
                  <option value={10}>10</option>
                  <option value={25}>25</option>
                  <option value={50}>50</option>
                </select>
                <span className="ml-2">
                  Page <strong>{resPage}</strong> of <strong>{totalPages}</strong> ({total} total results)
                </span>
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => setResPage((p) => Math.max(1, p - 1))}
                  disabled={resPage <= 1 || resultsLoading}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40 cursor-pointer"
                >
                  <ChevronLeft className="w-3.5 h-3.5" />
                  Previous
                </button>
                <button
                  onClick={() => setResPage((p) => Math.min(totalPages, p + 1))}
                  disabled={resPage >= totalPages || resultsLoading}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-white border border-slate-200 rounded-lg font-medium text-slate-700 hover:bg-slate-100 disabled:opacity-40 cursor-pointer"
                >
                  Next
                  <ChevronRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // =========================================================================
  // VIEW 2: UNIVERSAL SEARCH BUILDER & PREVIOUS SEARCH HISTORY
  // =========================================================================
  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Universal Lead Discovery</h1>
          <p className="text-sm text-slate-500 mt-1">
            Search any company, industry, business category, or location dynamically across live public sources.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchJobsAndProviders}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 shadow-sm cursor-pointer"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button
            onClick={onNavigateToLeads}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700 shadow-sm cursor-pointer"
          >
            View All Discovered Leads &rarr;
          </button>
        </div>
      </div>

      {/* Compliance & Live Data Integrity Notice */}
      <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-200/80 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
        <div className="text-xs text-blue-900 leading-relaxed">
          <span className="font-bold">Live Dynamic Retrieval &amp; Compliance Guarantee: </span>
          Live searches dynamically query OpenStreetMap / Overpass / Photon, Wikidata &amp; Wikipedia Business Graph, Company Domain Directories, and configured External Search APIs. Lead Shark respects <code className="bg-blue-100 px-1 py-0.5 rounded text-blue-800">robots.txt</code>, never fabricates emails or phone numbers, and keeps synthetic DEMO DATA strictly isolated from verified live records.
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column: Universal Discovery Search Form */}
        <div className="lg:col-span-2 bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-6">
          <div className="flex items-center gap-2 pb-4 border-b border-slate-100">
            <Compass className="w-5 h-5 text-blue-600" />
            <div>
              <h2 className="text-base font-semibold text-slate-900">Find Business Leads</h2>
              <p className="text-xs text-slate-500">
                Search for any specific company or industry + region (no predefined or hardcoded company limits).
              </p>
            </div>
          </div>

          <form onSubmit={handleCreateJob} className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Search Name (Optional)</label>
                <input
                  type="text"
                  placeholder="Auto-named from query if blank"
                  value={jobName}
                  onChange={(e) => setJobName(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Data Source</label>
                <select
                  value={source}
                  onChange={(e) => setSource(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                >
                  <option value="all">All Live Public Sources (Universal Dynamic Search)</option>
                  <option value="wikidata">Wikidata &amp; Wikipedia Business Graph</option>
                  <option value="osm">OpenStreetMap / Overpass / Photon Map Directory</option>
                  <option value="external_search">External Search APIs (Places / Serper / DDG)</option>
                  <option value="company_directory">Public Company Domain Directory</option>
                  <option value="website">Company Website URL (robots.txt compliant)</option>
                  <option value="demo">Demo Data Only (Clearly Labeled Synthetic Samples)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Company / Business Search</label>
              <input
                type="text"
                placeholder="e.g. Amazon, Wipro, IT companies in Hyderabad, Manufacturing companies in India..."
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                required
              />
              {/* Quick Example Prompts */}
              <div className="mt-2.5 flex flex-wrap items-center gap-1.5">
                <span className="text-[11px] text-slate-400 font-medium mr-1">Try:</span>
                {EXAMPLE_SEARCHES.map((ex) => (
                  <button
                    key={ex}
                    type="button"
                    onClick={() => setQuery(ex)}
                    className="px-2 py-0.5 rounded-md bg-slate-100 hover:bg-blue-50 hover:text-blue-700 text-slate-600 text-[11px] font-medium transition cursor-pointer"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Target Region</label>
                <select
                  value={region}
                  onChange={(e) => setRegion(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                >
                  <option value="Global">Global (All Regions)</option>
                  <option value="North America">North America</option>
                  <option value="Europe (UK/EU)">Europe (UK/EU)</option>
                  <option value="Asia-Pacific">Asia-Pacific</option>
                  <option value="Middle East & Africa">Middle East &amp; Africa</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Country (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. India, United States"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Industry Focus</label>
                <select
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                >
                  <option value="All">All Industries</option>
                  <option value="Information Technology">Information Technology</option>
                  <option value="Manufacturing & Industrial">Manufacturing &amp; Industrial</option>
                  <option value="Healthcare & Life Sciences">Healthcare &amp; Life Sciences</option>
                  <option value="Financial Services">Financial Services</option>
                  <option value="Retail & E-Commerce">Retail &amp; E-Commerce</option>
                  <option value="Professional & Legal Services">Professional &amp; Legal Services</option>
                  <option value="CleanTech & Energy">CleanTech &amp; Energy</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Max Results</label>
                <input
                  type="number"
                  min="5"
                  max="100"
                  value={maxResults}
                  onChange={(e) => setMaxResults(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500"
                />
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={searching}
                className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 text-white font-semibold text-sm rounded-lg shadow-sm flex items-center justify-center gap-2 transition disabled:opacity-50 cursor-pointer"
              >
                {searching ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    Querying Live External Sources...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 fill-white" />
                    Search &amp; Find Leads
                  </>
                )}
              </button>
            </div>
          </form>
        </div>

        {/* Right Column: Configured Sources & Direct CSV Import */}
        <div className="space-y-6">
          {/* Active External Providers Status */}
          <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-3">
            <div className="flex items-center gap-2 pb-2.5 border-b border-slate-100">
              <Globe className="w-4 h-4 text-blue-600" />
              <h2 className="text-sm font-semibold text-slate-900">Configured Source Adapters</h2>
            </div>
            <div className="space-y-2 text-[11px]">
              {providers
                .filter((p) => p.id !== 'all' && p.id !== 'demo')
                .map((p) => (
                  <div key={p.id} className="flex items-center justify-between gap-2">
                    <span className="text-slate-700 font-medium truncate">{p.name}</span>
                    <span
                      className={`px-1.5 py-0.5 rounded font-bold text-[10px] shrink-0 ${
                        p.configured
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-slate-100 text-slate-500'
                      }`}
                    >
                      {p.configured ? 'ACTIVE' : 'KEY NEEDED'}
                    </span>
                  </div>
                ))}
            </div>
          </div>

          {/* Direct CSV Import Card */}
          <div className="bg-white p-5 rounded-xl border border-slate-200/80 shadow-xs space-y-4">
            <div className="flex items-center gap-2 pb-2.5 border-b border-slate-100">
              <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
              <h2 className="text-sm font-semibold text-slate-900">Direct CSV Import</h2>
            </div>
            <p className="text-xs text-slate-500 leading-relaxed">
              Upload prospect files or conference sheets. Automatic duplicate detection runs on ingestion.
            </p>

            <div className="border-2 border-dashed border-slate-200 rounded-lg p-4 text-center hover:bg-slate-50/60 transition cursor-pointer">
              <input
                type="file"
                accept=".csv"
                onChange={(e) => setCsvFile(e.target.files?.[0] || null)}
                className="hidden"
                id="csv-file-input"
              />
              <label htmlFor="csv-file-input" className="cursor-pointer block">
                <Upload className="w-6 h-6 text-slate-400 mx-auto mb-1.5" />
                <span className="text-xs font-semibold text-blue-600 hover:underline">
                  {csvFile ? csvFile.name : 'Click to select CSV file'}
                </span>
                <span className="block text-[11px] text-slate-400 mt-0.5">
                  Required column: <code className="bg-slate-100 px-1 py-0.5 rounded text-slate-700">email</code>
                </span>
              </label>
            </div>

            {csvFile && (
              <button
                onClick={handleCsvUpload}
                disabled={loading}
                className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-lg shadow-sm transition cursor-pointer"
              >
                Upload &amp; Deduplicate
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

      {/* Previous Lead Searches Table */}
      <div className="bg-white rounded-xl border border-slate-200/80 shadow-xs overflow-hidden">
        <div className="p-5 border-b border-slate-200 flex items-center justify-between">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Previous Lead Searches</h2>
            <p className="text-xs text-slate-500">
              Revisit any previous search independently to inspect discovered companies, contacts, source URLs, and filters.
            </p>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-slate-700">
            <thead className="bg-slate-50/70 border-b border-slate-200 text-[11px] uppercase tracking-wider text-slate-500 font-semibold">
              <tr>
                <th className="px-5 py-3.5">Search Name</th>
                <th className="px-5 py-3.5">Mode &amp; Data Source</th>
                <th className="px-5 py-3.5">Region</th>
                <th className="px-5 py-3.5">Status</th>
                <th className="px-5 py-3.5">Total Found</th>
                <th className="px-5 py-3.5">New Added</th>
                <th className="px-5 py-3.5">Duplicates</th>
                <th className="px-5 py-3.5">Date &amp; Time</th>
                <th className="px-5 py-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 text-xs">
              {jobs.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-5 py-8 text-center text-slate-400">
                    No lead searches on record yet. Use "Find Business Leads" above to execute a dynamic search.
                  </td>
                </tr>
              ) : (
                jobs.map((job) => {
                  const isDemo = job.data_mode === 'demo' || job.source === 'demo';
                  return (
                    <tr key={job.id} className="hover:bg-slate-50/50 transition">
                      <td className="px-5 py-3.5">
                        <div className="font-semibold text-slate-900">{job.job_name}</div>
                        <div className="text-[11px] text-slate-500 italic">"{job.query}"</div>
                      </td>
                      <td className="px-5 py-3.5">
                        <span
                          className={`uppercase text-[10px] px-1.5 py-0.5 rounded font-bold mr-1.5 ${
                            isDemo
                              ? 'bg-amber-100 text-amber-800 border border-amber-300'
                              : 'bg-emerald-100 text-emerald-800'
                          }`}
                        >
                          {isDemo ? 'DEMO' : 'LIVE'}
                        </span>
                        <span className="uppercase text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-700 font-bold">
                          {job.source}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 text-slate-600">{job.region || 'Global'}</td>
                      <td className="px-5 py-3.5">
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold ${
                            job.status === 'completed'
                              ? 'bg-emerald-100 text-emerald-800'
                              : job.status === 'running'
                              ? 'bg-blue-100 text-blue-800 animate-pulse'
                              : 'bg-rose-100 text-rose-800'
                          }`}
                        >
                          {job.status.toUpperCase()}
                        </span>
                      </td>
                      <td className="px-5 py-3.5 font-bold text-slate-800">{job.total_found}</td>
                      <td className="px-5 py-3.5 font-bold text-emerald-600">+{job.new_leads_count}</td>
                      <td className="px-5 py-3.5 text-slate-400">{job.duplicates_skipped}</td>
                      <td className="px-5 py-3.5 text-slate-400 font-mono text-[11px]">
                        {new Date(job.created_at).toLocaleString()}
                      </td>
                      <td className="px-5 py-3.5 text-right whitespace-nowrap">
                        <button
                          onClick={() => handleOpenJobResultsPage(job)}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-lg shadow-2xs transition cursor-pointer"
                        >
                          <Eye className="w-3.5 h-3.5 text-blue-600" />
                          View Found Leads
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

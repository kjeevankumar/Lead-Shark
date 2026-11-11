import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, ShieldCheck, Server, Globe, MapPin, Key, Check } from 'lucide-react';
import { api } from '../services/api';
import { UserRole } from '../types';

interface SettingsProps {
  currentRole: UserRole;
  onRoleChange: (r: UserRole) => void;
}

export const Settings: React.FC<SettingsProps> = ({ currentRole, onRoleChange }) => {
  const [dnsHealth, setDnsHealth] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.getDnsHealth().then(setDnsHealth).catch(console.error);
  }, []);

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900 tracking-tight">System Settings & Compliance Controls</h1>
        <p className="text-sm text-slate-500 mt-1">
          Sending domain DNS verification, sender identification, and security access parameters.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Domain Health & DNS Authentication */}
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Globe className="w-5 h-5 text-blue-600" />
            <h2 className="text-base font-semibold text-slate-900">Sending Domain & DNS Health</h2>
          </div>

          <div className="space-y-3 text-xs">
            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div>
                <span className="font-semibold text-slate-800">Sending Subdomain</span>
                <div className="text-slate-500 font-mono mt-0.5">{dnsHealth?.domain || 'mail.leadshark.io'}</div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">
                Dedicated Subdomain
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div>
                <span className="font-semibold text-slate-800">SPF Record (Sender Policy Framework)</span>
                <div className="text-slate-500 font-mono mt-0.5">v=spf1 include:_spf.leadshark.io ~all</div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 flex items-center gap-1">
                <Check className="w-3 h-3" /> Valid
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div>
                <span className="font-semibold text-slate-800">DKIM Authentication</span>
                <div className="text-slate-500 font-mono mt-0.5">k=rsa; p=MIGfMA0GCSqGSIb3DQEBA...</div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 flex items-center gap-1">
                <Check className="w-3 h-3" /> 2048-bit Key
              </span>
            </div>

            <div className="flex items-center justify-between p-3 bg-slate-50 rounded-lg border border-slate-200">
              <div>
                <span className="font-semibold text-slate-800">DMARC Enforcement</span>
                <div className="text-slate-500 font-mono mt-0.5">v=DMARC1; p=reject; rua=mailto:dmarc@...</div>
              </div>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800 flex items-center gap-1">
                <Check className="w-3 h-3" /> Enforced
              </span>
            </div>
          </div>
        </div>

        {/* Sender Identification & Physical Address */}
        <div className="bg-white p-6 rounded-xl border border-slate-200/80 shadow-xs space-y-5">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <MapPin className="w-5 h-5 text-emerald-600" />
            <h2 className="text-base font-semibold text-slate-900">Mandatory Compliance Footer & Address</h2>
          </div>

          <div className="space-y-3 text-xs">
            <p className="text-slate-500 leading-relaxed">
              CAN-SPAM and GDPR require a truthful physical postal address on all outbound communications. The sending engine blocks campaign launches if this setting is empty.
            </p>

            <div>
              <label className="block font-semibold text-slate-700 mb-1">Company Physical Address</label>
              <textarea
                readOnly
                rows={3}
                value={dnsHealth?.postal_address || '100 Innovation Way, Suite 500, Tech District, CA 94105, USA'}
                className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-slate-800 font-mono"
              />
            </div>

            <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-900">
              <span className="font-bold">Active Outbound Mode: </span>
              <span className="font-mono">{dnsHealth?.sending_mode || 'safe_demo'}</span>
              <p className="text-[11px] text-emerald-700 mt-0.5">
                Outbound emails are processed via Safe Demo Simulation to protect deliverability and prevent unsolicited blasting.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

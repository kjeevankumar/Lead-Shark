import React, { useState, useEffect } from 'react';
import { ShieldCheck, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../services/api';

interface PublicUnsubscribeProps {
  token: string;
}

export const PublicUnsubscribe: React.FC<PublicUnsubscribeProps> = ({ token }) => {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [email, setEmail] = useState<string>('');

  useEffect(() => {
    if (!token) return;
    api.publicUnsubscribe(token)
      .then((data) => {
        setStatus('success');
        setEmail(data.email);
      })
      .catch((err) => {
        setStatus('error');
      });
  }, [token]);

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white border border-slate-200 rounded-2xl shadow-xl max-w-md w-full p-8 text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto text-xl font-bold">
          <ShieldCheck className="w-6 h-6" />
        </div>

        <h1 className="text-xl font-bold text-slate-900">One-Click Opt-Out Confirmed</h1>

        {status === 'loading' && (
          <p className="text-xs text-slate-500">Processing global suppression preference...</p>
        )}

        {status === 'success' && (
          <div className="space-y-3">
            <p className="text-xs text-slate-600 leading-relaxed">
              Your email address has been permanently added to the Lead Shark Global Suppression Registry.
            </p>
            {email && (
              <div className="px-3 py-1.5 bg-slate-100 rounded-lg text-xs font-mono font-bold text-blue-600">
                {email}
              </div>
            )}
            <p className="text-[11px] text-slate-400">
              Preference updated immediately in compliance with CAN-SPAM and GDPR Article 21.
            </p>
          </div>
        )}

        {status === 'error' && (
          <div className="space-y-2 text-rose-600">
            <p className="text-xs font-semibold">Could not verify unsubscribe token.</p>
            <p className="text-[11px] text-slate-400">
              Your email might already be suppressed, or the link has expired.
            </p>
          </div>
        )}

        <div className="pt-4 border-t border-slate-100 text-[10px] text-slate-400">
          Lead Shark Lead Intelligence Platform &bull; Global Suppression Registry
        </div>
      </div>
    </div>
  );
};

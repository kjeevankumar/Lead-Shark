import React, { useState } from 'react';
import { Search, Bell, Shield, User as UserIcon, RefreshCw } from 'lucide-react';
import { UserRole } from '../types';

interface TopNavbarProps {
  currentRole: UserRole;
  onRoleChange: (newRole: UserRole) => void;
  searchTerm: string;
  onSearchChange: (val: string) => void;
  apiConnected: boolean;
}

export const TopNavbar: React.FC<TopNavbarProps> = ({
  currentRole,
  onRoleChange,
  searchTerm,
  onSearchChange,
  apiConnected
}) => {
  const [showRoleMenu, setShowRoleMenu] = useState(false);

  const roleLabels: Record<UserRole, { title: string; color: string; desc: string }> = {
    admin: { title: 'Admin', color: 'bg-purple-100 text-purple-700 border-purple-300', desc: 'Full application & suppression access' },
    reviewer: { title: 'Reviewer', color: 'bg-blue-100 text-blue-700 border-blue-300', desc: 'Can approve leads & campaign outreach' },
    sales: { title: 'Sales User', color: 'bg-emerald-100 text-emerald-700 border-emerald-300', desc: 'Creates jobs, leads & campaign drafts' },
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-20 shadow-sm">
      {/* Search Input */}
      <div className="flex items-center gap-3 w-96">
        <div className="relative w-full">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            placeholder="Search leads, companies, domains, sectors..."
            value={searchTerm}
            onChange={(e) => onSearchChange(e.target.value)}
            className="w-full pl-9 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-500 transition-all"
          />
        </div>
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* Backend Connectivity Status */}
        <div className="flex items-center gap-2 px-3 py-1 bg-slate-50 border border-slate-200 rounded-full text-xs font-medium text-slate-600">
          <span className={`w-2 h-2 rounded-full ${apiConnected ? 'bg-emerald-500 animate-pulse' : 'bg-red-400'}`}></span>
          <span>{apiConnected ? 'API Connected' : 'Connecting to API...'}</span>
        </div>

        {/* Live RBAC Role Switcher */}
        <div className="relative">
          <button
            onClick={() => setShowRoleMenu(!showRoleMenu)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 shadow-sm transition-colors"
          >
            <Shield className="w-3.5 h-3.5 text-blue-600" />
            <span>Role:</span>
            <span className={`px-2 py-0.5 rounded text-[11px] font-bold border ${roleLabels[currentRole].color}`}>
              {roleLabels[currentRole].title}
            </span>
          </button>

          {showRoleMenu && (
            <div className="absolute right-0 mt-2 w-64 bg-white border border-slate-200 rounded-xl shadow-xl py-2 z-50 animate-in fade-in slide-in-from-top-1 duration-150">
              <div className="px-3 py-1.5 border-b border-slate-100 text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Switch Live User Role
              </div>
              {(['admin', 'reviewer', 'sales'] as UserRole[]).map((r) => (
                <button
                  key={r}
                  onClick={() => {
                    onRoleChange(r);
                    setShowRoleMenu(false);
                  }}
                  className={`w-full text-left px-3 py-2 text-xs flex flex-col gap-0.5 hover:bg-slate-50 transition-colors ${
                    currentRole === r ? 'bg-blue-50/60 font-semibold text-blue-900' : 'text-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span>{roleLabels[r].title}</span>
                    {currentRole === r && <span className="text-[10px] text-blue-600 font-bold">Active</span>}
                  </div>
                  <span className="text-[10px] text-slate-400 font-normal">{roleLabels[r].desc}</span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Notifications Icon */}
        <button className="w-9 h-9 rounded-lg border border-slate-200 flex items-center justify-center text-slate-500 hover:text-slate-800 hover:bg-slate-50 transition-colors relative">
          <Bell className="w-4 h-4" />
          <span className="w-2 h-2 rounded-full bg-blue-600 absolute top-2 right-2"></span>
        </button>

        {/* User Profile */}
        <div className="flex items-center gap-2.5 pl-2 border-l border-slate-200">
          <div className="w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center text-xs font-bold">
            LS
          </div>
          <div className="hidden md:block text-left">
            <div className="text-xs font-semibold text-slate-900 capitalize">{currentRole} User</div>
            <div className="text-[10px] text-slate-400">{currentRole}@leadshark.io</div>
          </div>
        </div>
      </div>
    </header>
  );
};

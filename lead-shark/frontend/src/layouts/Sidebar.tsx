import React from 'react';
import { 
  LayoutDashboard, Compass, Users, ShieldCheck, Cpu, 
  Send, Ban, BarChart3, FileText, Settings, ShieldAlert, Sparkles 
} from 'lucide-react';

interface SidebarProps {
  currentTab: string;
  setCurrentTab: (tab: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, setCurrentTab }) => {
  const navItems = [
    { id: 'overview', label: 'Overview', icon: LayoutDashboard },
    { id: 'discovery', label: 'Lead Discovery', icon: Compass },
    { id: 'leads', label: 'All Leads', icon: Users },
    { id: 'verification', label: 'Enrichment & Verification', icon: ShieldCheck },
    { id: 'segmentation', label: 'Segmentation (RAG)', icon: Cpu },
    { id: 'campaigns', label: 'Campaigns', icon: Send },
    { id: 'suppression', label: 'Suppression List', icon: Ban },
    { id: 'analytics', label: 'Analytics', icon: BarChart3 },
    { id: 'audit', label: 'Audit Logs', icon: FileText },
    { id: 'settings', label: 'Settings', icon: Settings },
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 h-screen sticky top-0 border-r border-slate-800 shadow-xl select-none z-30">
      {/* Brand Header */}
      <div className="h-16 flex items-center px-6 border-b border-slate-800/80 gap-3 bg-slate-950/40">
        <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-blue-600 to-sky-400 flex items-center justify-center text-white shadow-md shadow-blue-500/20 font-black tracking-wider text-lg">
          🦈
        </div>
        <div>
          <div className="font-bold text-white text-base tracking-tight flex items-center gap-1.5">
            LEAD SHARK
            <span className="text-[10px] uppercase font-semibold tracking-wider px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
              v1.0
            </span>
          </div>
          <div className="text-[11px] text-slate-400 font-medium">Compliant Lead Intelligence</div>
        </div>
      </div>

      {/* Navigation List */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
          Platform Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setCurrentTab(item.id)}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 text-left ${
                isActive
                  ? 'bg-blue-600 text-white shadow-sm shadow-blue-600/30'
                  : 'text-slate-300 hover:bg-slate-800/70 hover:text-white'
              }`}
            >
              <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-white' : 'text-slate-400'}`} />
              <span className="truncate">{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Footer Compliance Badge */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/30 space-y-2">
        <div className="flex items-center gap-2 px-2.5 py-2 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-[11px] text-emerald-400">
          <ShieldAlert className="w-3.5 h-3.5 shrink-0 text-emerald-400" />
          <span className="font-medium">CAN-SPAM & GDPR Protected</span>
        </div>
        <div className="flex items-center justify-between text-[11px] text-slate-400 px-1">
          <span className="flex items-center gap-1">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
            Safe Demo Sending
          </span>
          <span>v1.0.0</span>
        </div>
      </div>
    </aside>
  );
};

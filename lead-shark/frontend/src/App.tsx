import React, { useState, useEffect } from 'react';
import { Sidebar } from './layouts/Sidebar';
import { TopNavbar } from './layouts/TopNavbar';
import { Overview } from './pages/Overview';
import { LeadDiscovery } from './pages/LeadDiscovery';
import { AllLeads } from './pages/AllLeads';
import { EnrichmentVerification } from './pages/EnrichmentVerification';
import { Segmentation } from './pages/Segmentation';
import { Campaigns } from './pages/Campaigns';
import { SuppressionList } from './pages/SuppressionList';
import { Analytics } from './pages/Analytics';
import { AuditLogs } from './pages/AuditLogs';
import { Settings } from './pages/Settings';
import { PublicUnsubscribe } from './pages/PublicUnsubscribe';
import { api } from './services/api';
import { UserRole } from './types';

export const App: React.FC = () => {
  const [currentTab, setCurrentTab] = useState('overview');
  const [currentRole, setCurrentRole] = useState<UserRole>('admin');
  const [searchTerm, setSearchTerm] = useState('');
  const [apiConnected, setApiConnected] = useState(false);

  // Check if current route is a public unsubscribe link
  const path = window.location.pathname;
  if (path.startsWith('/unsubscribe/')) {
    const token = path.replace('/unsubscribe/', '');
    return <PublicUnsubscribe token={token} />;
  }

  useEffect(() => {
    // Initial health check and login
    const initApp = async () => {
      try {
        await api.checkHealth();
        setApiConnected(true);
        // Default login as admin for seamless evaluation
        await api.login('admin@leadshark.io', 'LeadShark2026!');
      } catch (err) {
        console.warn('Initial backend connection note:', err);
        setApiConnected(false);
      }
    };
    initApp();

    const interval = setInterval(() => {
      api.checkHealth()
        .then(() => setApiConnected(true))
        .catch(() => setApiConnected(false));
    }, 15000);

    return () => clearInterval(interval);
  }, []);

  const handleRoleChange = async (newRole: UserRole) => {
    setCurrentRole(newRole);
    try {
      await api.switchDemoRole(newRole);
    } catch (err) {
      console.error('Role switch error:', err);
    }
  };

  const renderContent = () => {
    switch (currentTab) {
      case 'overview':
        return <Overview onNavigate={setCurrentTab} />;
      case 'discovery':
        return <LeadDiscovery onNavigateToLeads={() => setCurrentTab('leads')} />;
      case 'leads':
        return <AllLeads currentRole={currentRole} globalSearch={searchTerm} />;
      case 'verification':
        return <EnrichmentVerification />;
      case 'segmentation':
        return <Segmentation />;
      case 'campaigns':
        return <Campaigns currentRole={currentRole} />;
      case 'suppression':
        return <SuppressionList currentRole={currentRole} />;
      case 'analytics':
        return <Analytics />;
      case 'audit':
        return <AuditLogs />;
      case 'settings':
        return <Settings currentRole={currentRole} onRoleChange={handleRoleChange} />;
      default:
        return <Overview onNavigate={setCurrentTab} />;
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50 font-sans antialiased text-slate-900">
      <Sidebar currentTab={currentTab} setCurrentTab={setCurrentTab} />
      <div className="flex-1 flex flex-col min-w-0">
        <TopNavbar
          currentRole={currentRole}
          onRoleChange={handleRoleChange}
          searchTerm={searchTerm}
          onSearchChange={setSearchTerm}
          apiConnected={apiConnected}
        />
        <main className="flex-1 overflow-y-auto">
          {renderContent()}
        </main>
      </div>
    </div>
  );
};

export default App;

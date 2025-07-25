import React from 'react';
import { Container, Nav, NavItem, NavLink, TabContent, TabPane } from 'reactstrap';
import { useState } from 'react';
import { ProtectedAdminPlanManager } from './AdminPlanManager';

// Diğer admin bileşenleri import edilebilir (ör: UserManagement, LogsPanel vs.)

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('plans');

  return (
    <Container className="mt-4">
      <h2>Admin Panel</h2>
      <Nav tabs>
        <NavItem>
          <NavLink
            className={activeTab === 'plans' ? 'active' : ''}
            onClick={() => setActiveTab('plans')}
          >
            Plan Yönetimi
          </NavLink>
        </NavItem>
        {/* Diğer sekmeler */}
      </Nav>

      <TabContent activeTab={activeTab} className="mt-3">
        <TabPane tabId="plans">
          <ProtectedAdminPlanManager />
        </TabPane>
        {/* Diğer tabpanes */}
      </TabContent>
    </Container>
  );
}

import React from 'react';
import { Route, Routes, useParams } from 'react-router-dom';
import AdminDashboard from '../pages/AdminDashboard';
import AdminUsers from '../pages/AdminUsers';
import AdminPromos from '../pages/AdminPromos';
import AdminPredictions from '../pages/AdminPredictions';
import AdminPlanManager from '../pages/AdminPlanManager';
import AdminLimits from '../pages/AdminLimits';
import AdminContent from '../pages/AdminContent';
import AdminMonitoring from '../pages/AdminMonitoring';
import AdminLogs from '../pages/AdminLogs';
import AdminFeatureFlags from '../pages/AdminFeatureFlags';
import AdminDraks from '../pages/AdminDraks';
import UserDetail from './UserDetail';

const AdminRoutes = () => {
  return (
    <Routes>
      <Route index element={<AdminDashboard />} />
      <Route path="users" element={<AdminUsers />} />
      <Route path="users/:id" element={<AdminUserDetailRoute />} />
      <Route path="promos" element={<AdminPromos />} />
      <Route path="predictions" element={<AdminPredictions />} />
      <Route path="plans" element={<AdminPlanManager />} />
      <Route path="limits" element={<AdminLimits />} />
      <Route path="content" element={<AdminContent />} />
      <Route path="monitoring" element={<AdminMonitoring />} />
      <Route path="draks" element={<AdminDraks />} />
      <Route path="feature-flags" element={<AdminFeatureFlags />} />
      <Route path="logs" element={<AdminLogs />} />
    </Routes>
  );
};

function AdminUserDetailRoute() {
  const { id } = useParams<{ id: string }>();
  return <UserDetail userId={id!} />;
}

export default AdminRoutes;


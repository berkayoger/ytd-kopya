import React from 'react';
import { Route, Routes, useParams } from 'react-router-dom';
import AdminDashboard from './pages/AdminDashboard';
import AdminUsers from './pages/AdminUsers';
import AdminPromos from './pages/AdminPromos';
import AdminPredictions from './pages/AdminPredictions';
import AdminPlanManager from './pages/AdminPlanManager';
import AdminLimits from './pages/AdminLimits';
import AdminContent from './pages/AdminContent';
import AdminMonitoring from './pages/AdminMonitoring';
import AdminLogs from './pages/AdminLogs';
import AdminFeatureFlags from './pages/AdminFeatureFlags';
import UserDetail from './admin/UserDetail';

const AdminRoutes = () => {
  return (
    <Routes>
      <Route path="/admin" element={<AdminDashboard />} />
      <Route path="/admin/users" element={<AdminUsers />} />
      <Route path="/admin/users/:id" element={<AdminUserDetailRoute />} />
      <Route path="/admin/promos" element={<AdminPromos />} />
      <Route path="/admin/predictions" element={<AdminPredictions />} />
      <Route path="/admin/plans" element={<AdminPlanManager />} />
      <Route path="/admin/limits" element={<AdminLimits />} />
      <Route path="/admin/content" element={<AdminContent />} />
      <Route path="/admin/monitoring" element={<AdminMonitoring />} />
      <Route path="/admin/feature-flags" element={<AdminFeatureFlags />} />
      <Route path="/admin/logs" element={<AdminLogs />} />
    </Routes>
  );
};

// Route bileşeni, URL parametresinden kullanıcı ID'sini alır
function AdminUserDetailRoute() {
  const { id } = useParams<{ id: string }>();
  return <UserDetail userId={id!} />;
}

export default AdminRoutes;

import { Route, Routes } from 'react-router-dom';
import AdminDashboard from './pages/AdminDashboard';
import AdminUsers from './pages/AdminUsers';
import AdminPromos from './pages/AdminPromos';
import AdminPredictions from './pages/AdminPredictions';
import AdminPlanManager from './pages/AdminPlanManager';
import AdminLimits from './pages/AdminLimits';
import AdminContent from './pages/AdminContent';
import AdminMonitoring from './pages/AdminMonitoring';
import AdminLogs from './pages/AdminLogs';

const AdminRoutes = () => {
  return (
    <Routes>
      <Route path="/admin" element={<AdminDashboard />} />
      <Route path="/admin/users" element={<AdminUsers />} />
      <Route path="/admin/promos" element={<AdminPromos />} />
      <Route path="/admin/predictions" element={<AdminPredictions />} />
      <Route path="/admin/plans" element={<AdminPlanManager />} />
      <Route path="/admin/limits" element={<AdminLimits />} />
      <Route path="/admin/content" element={<AdminContent />} />
      <Route path="/admin/monitoring" element={<AdminMonitoring />} />
      <Route path="/admin/logs" element={<AdminLogs />} />
    </Routes>
  );
};

export default AdminRoutes;

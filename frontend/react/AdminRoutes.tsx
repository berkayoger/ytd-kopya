import React from 'react';
import { Route, Routes } from 'react-router-dom';
import AdminPlanManager from './AdminPlanManager';
import { ProtectedRoute } from './ProtectedRoute';

function AdminRoutes() {
  return (
    <Routes>
      {/* Diğer admin route'ları */}
      <Route
        path="/admin/plans"
        element={
          <ProtectedRoute isAdmin={true}>
            <AdminPlanManager />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default AdminRoutes;

import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export default function withAdminGuard<P>(Component: React.ComponentType<P>) {
  return function GuardedComponent(props: P) {
    const { user, loading } = useAuth();

    if (loading) {
      return <div>Yükleniyor...</div>;
    }

    if (!user || !user.is_admin) {
      return <Navigate to="/unauthorized" replace />;
    }

    return <Component {...props} />;
  };
}

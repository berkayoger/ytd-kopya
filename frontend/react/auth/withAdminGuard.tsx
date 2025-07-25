import React from 'react';
import { Navigate } from 'react-router-dom';

export default function withAdminGuard<P>(Component: React.ComponentType<P>) {
  return function GuardedComponent(props: P) {
    const token = sessionStorage.getItem('admin_jwt');
    if (!token) {
      return <Navigate to="/unauthorized" />;
    }
    return <Component {...props} />;
  };
}

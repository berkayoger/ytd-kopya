import { Navigate } from 'react-router-dom';

export function ProtectedRoute({ isAdmin, children }: { isAdmin: boolean; children: JSX.Element }) {
  if (!isAdmin) {
    return <Navigate to="/unauthorized" />;
  }
  return children;
}

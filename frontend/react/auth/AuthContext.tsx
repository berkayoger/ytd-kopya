import React, { createContext, useContext, useState, useEffect } from 'react';

interface AuthUser {
  id: number;
  username: string;
  is_admin: boolean;
}

interface AuthContextState {
  user: AuthUser | null;
  loading: boolean;
}

const AuthContext = createContext<AuthContextState>({ user: null, loading: true });

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a real app, fetch the current user from an API or storage
    const stored = localStorage.getItem('user');
    if (stored) {
      try {
        setUser(JSON.parse(stored));
      } catch {
        setUser(null);
      }
    }
    setLoading(false);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

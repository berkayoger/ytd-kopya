import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardContent } from "./components/ui/card";

// Admin kullanıcılarını listeleyen basit bileşen
interface User {
  id: number;
  username: string;
  email: string;
  subscription_level: string;
}

export default function UserManagement() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Kullanıcı listesini API'den çek
  useEffect(() => {
    let mounted = true;

    async function loadUsers() {
      setLoading(true);
      setError(null);
      try {
        const headers: Record<string, string> = {
          "Content-Type": "application/json",
          "X-CSRF-TOKEN": "admin",
        };
        const token = localStorage.getItem("access_token");
        const apiKey = localStorage.getItem("api_key");
        if (token) headers["Authorization"] = `Bearer ${token}`;
        if (apiKey) headers["X-API-KEY"] = apiKey;

        const resp = await fetch("/api/admin/users/", {
          method: "GET",
          headers,
          credentials: "include",
        });
        if (!resp.ok) {
          const txt = await resp.text();
          throw new Error(`HTTP ${resp.status} ${txt || ""}`.trim());
        }
        const data = await resp.json();
        if (mounted) setUsers(data);
      } catch (e: any) {
        if (mounted) setError(e?.message || "Yüklenemedi");
      } finally {
        if (mounted) setLoading(false);
      }
    }

    loadUsers();
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) return <div>Yükleniyor...</div>;
  if (error) return <div className="text-red-600">{error}</div>;

  return (
    <Card>
      <CardContent className="space-y-2 p-4">
        {users.map((user) => (
          <div
            key={user.id}
            className="grid grid-cols-4 gap-2 items-center text-sm"
          >
            <div>{user.username}</div>
            <div>{user.email}</div>
            <div>{user.subscription_level}</div>
            <Link
              to={`/admin/users/${user.id}`}
              className="text-blue-500 hover:underline text-sm"
            >
              Detay
            </Link>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

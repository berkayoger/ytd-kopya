import React, { useState, useEffect } from 'react';
import { Input, Button } from 'reactstrap';

interface User {
  id: number;
  username: string;
  subscription_level: string;
  custom_features?: string;
}

export default function CustomFeaturesEditor() {
  const [users, setUsers] = useState<User[]>([]);
  const [selectedUser, setSelectedUser] = useState<string>('');
  const [customFeatures, setCustomFeatures] = useState<string>('{}');
  const [status, setStatus] = useState('');

  useEffect(() => {
    fetch('/api/admin/users')
      .then(res => res.json())
      .then(data => setUsers(data))
      .catch(() => setStatus('Kullanıcılar yüklenemedi.'));
  }, []);

  const loadUserFeatures = (userId: string) => {
    setSelectedUser(userId);
    const user = users.find(u => u.id === Number(userId));
    setCustomFeatures(user?.custom_features || '{}');
  };

  const saveCustomFeatures = () => {
    fetch(`/api/admin/users/${selectedUser}/custom-features`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ custom_features: customFeatures }),
    })
      .then(res => {
        if (!res.ok) throw new Error('Hata');
        return res.json();
      })
      .then(() => setStatus('Kaydedildi.'))
      .catch(() => setStatus('Kaydedilemedi.'));
  };

  return (
    <div className="p-4 text-white">
      <h2 className="text-xl font-semibold mb-4">Kullanıcıya Özel Özellikler</h2>

      <label className="block mb-2">Kullanıcı Seçin</label>
      <select
        className="mb-4 p-2 bg-slate-800 rounded"
        onChange={e => loadUserFeatures(e.target.value)}
        defaultValue=""
      >
        <option value="" disabled>
          Seçiniz
        </option>
        {users.map(user => (
          <option key={user.id} value={user.id}>
            {user.username} ({user.subscription_level})
          </option>
        ))}
      </select>

      {selectedUser && (
        <>
          <label className="block mb-2">custom_features JSON</label>
          <Input
            className="bg-slate-900 mb-4"
            value={customFeatures}
            onChange={e => setCustomFeatures(e.target.value)}
          />
          <Button onClick={saveCustomFeatures}>Kaydet</Button>
        </>
      )}

      {status && <p className="mt-2 text-sm text-slate-400">{status}</p>}
    </div>
  );
}

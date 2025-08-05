import React, { useEffect, useState } from 'react';
import { Switch } from './components/ui/switch';
import { toast } from 'sonner';

interface FeatureFlags {
  [key: string]: boolean;
}

const AdminFeatureFlags: React.FC = () => {
  const [flags, setFlags] = useState<FeatureFlags>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/admin/feature-flags')
      .then((res) => res.json())
      .then(setFlags)
      .finally(() => setLoading(false));
  }, []);

  const toggleFlag = (key: string, value: boolean) => {
    fetch(`/api/admin/feature-flags/${key}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: value }),
    })
      .then((res) => res.json())
      .then((data) => {
        setFlags((prev) => ({ ...prev, [key]: data[key] }));
        toast.success(`${key} güncellendi: ${data[key] ? 'açık' : 'kapalı'}`);
      })
      .catch(() => {
        toast.error('Güncelleme başarısız');
      });
  };

  if (loading) return <p>Yükleniyor...</p>;

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold mb-4">Feature Flag Yönetimi</h1>
      <ul className="space-y-4">
        {Object.entries(flags).map(([key, value]) => (
          <li
            key={key}
            className="flex items-center justify-between bg-muted p-4 rounded-xl shadow-sm"
          >
            <span className="font-medium">{key}</span>
            <Switch checked={value} onCheckedChange={(v) => toggleFlag(key, v)} />
          </li>
        ))}
      </ul>
    </div>
  );
};

export default AdminFeatureFlags;

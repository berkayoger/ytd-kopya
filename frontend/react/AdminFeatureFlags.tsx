import React, { useEffect, useState } from 'react';
import { Switch } from './components/ui/switch';
import { toast } from 'sonner';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';

interface FeatureFlags {
  [key: string]: {
    enabled: boolean;
    description?: string;
    category?: string;
  };
}

const AdminFeatureFlags: React.FC = () => {
  const [flags, setFlags] = useState<FeatureFlags>({});
  const [loading, setLoading] = useState(true);
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  const [newFlag, setNewFlag] = useState({
    name: '',
    description: '',
    category: '',
    enabled: false,
  });

  useEffect(() => {
    const endpoint = categoryFilter
      ? `/api/admin/feature-flags/category/${categoryFilter}`
      : '/api/admin/feature-flags';
    fetch(endpoint)
      .then((res) => res.json())
      .then(setFlags)
      .finally(() => setLoading(false));
  }, [categoryFilter]);

  const toggleFlag = (key: string, value: boolean) => {
    fetch(`/api/admin/feature-flags/${key}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: value }),
    })
      .then((res) => res.json())
      .then((data) => {
        setFlags((prev) => ({
          ...prev,
          [key]: {
            ...prev[key],
            enabled: data[key],
          },
        }));
        toast.success(`${key} güncellendi: ${data[key] ? 'açık' : 'kapalı'}`);
      })
      .catch(() => {
        toast.error('Güncelleme başarısız');
      });
  };

  if (loading) return <p>Yükleniyor...</p>;

  return (
    <div className="p-6 max-w-3xl space-y-8">
      <h1 className="text-2xl font-bold mb-4">Feature Flag Yönetimi</h1>
      <div className="flex items-center space-x-2">
        <Input
          placeholder="Kategoriye göre filtrele"
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
        />
        <Button onClick={() => setCategoryFilter('')}>Temizle</Button>
      </div>
      <div className="space-y-4">
        {Object.entries(flags).map(([key, info]) => (
          <div
            key={key}
            className="flex flex-col bg-muted p-4 rounded-xl shadow-sm"
          >
            <div className="flex justify-between items-center">
              <span className="font-medium">{key}</span>
              <Switch checked={info.enabled} onCheckedChange={(v) => toggleFlag(key, v)} />
            </div>
            <p className="text-sm text-muted-foreground">{info.description}</p>
            <span className="text-xs italic text-blue-600">{info.category}</span>
          </div>
        ))}
      </div>

      <div className="border-t pt-6 space-y-2">
        <h2 className="text-lg font-semibold">Yeni Flag Ekle</h2>
        <div className="flex flex-col space-y-2">
          <Input
            placeholder="Flag adı"
            value={newFlag.name}
            onChange={(e) => setNewFlag({ ...newFlag, name: e.target.value })}
          />
          <Input
            placeholder="Açıklama"
            value={newFlag.description}
            onChange={(e) => setNewFlag({ ...newFlag, description: e.target.value })}
          />
          <Input
            placeholder="Kategori"
            value={newFlag.category}
            onChange={(e) => setNewFlag({ ...newFlag, category: e.target.value })}
          />
          <div className="flex items-center space-x-2">
            <Switch
              checked={newFlag.enabled}
              onCheckedChange={(v) => setNewFlag({ ...newFlag, enabled: v })}
            />
            <span>{newFlag.enabled ? 'Açık' : 'Kapalı'}</span>
          </div>
          <Button
            onClick={() => {
              fetch('/api/admin/feature-flags/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(newFlag),
              })
                .then((res) => res.json())
                .then(() => {
                  toast.success(`${newFlag.name} eklendi`);
                  setNewFlag({ name: '', description: '', category: '', enabled: false });
                  return fetch('/api/admin/feature-flags')
                    .then((r) => r.json())
                    .then(setFlags);
                })
                .catch(() => toast.error('Ekleme başarısız'));
            }}
          >
            Ekle
          </Button>
        </div>
      </div>

      <div className="border-t pt-6 space-y-2">
        <h2 className="text-lg font-semibold">Export / Import</h2>
        <div className="flex flex-col space-y-2">
          <Button
            variant="outline"
            onClick={() => {
              fetch('/api/admin/feature-flags/export')
                .then((res) => res.json())
                .then((data) => {
                  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                  const url = URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = 'feature-flags.json';
                  a.click();
                });
            }}
          >
            Export JSON
          </Button>
          <textarea
            className="border p-2 rounded-md text-sm"
            placeholder="JSON yapıştırın..."
            rows={6}
            onBlur={(e) => {
              const parsed = JSON.parse(e.target.value);
              fetch('/api/admin/feature-flags/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(parsed),
              })
                .then((res) => res.json())
                .then(() => {
                  toast.success('Import başarılı');
                  return fetch('/api/admin/feature-flags')
                    .then((r) => r.json())
                    .then(setFlags);
                })
                .catch(() => toast.error('Import başarısız'));
            }}
          />
        </div>
      </div>
    </div>
  );
};

export default AdminFeatureFlags;

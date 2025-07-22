import React from 'react';
import useLimitStatus from './hooks/useLimitStatus';
import { Card, CardBody, Progress, Spinner } from 'reactstrap';
import { AlertTriangle, ShieldCheck } from 'lucide-react';

const limitLabels: Record<string, string> = {
  predict_daily: 'Günlük Tahmin',
  generate_chart: 'Grafik Üretme',
  export: 'Veri Dışa Aktarma',
  forecast: 'Tahmin Analizi',
  prediction: 'Model Tahmini',
};

export default function PlanLimitCard() {
  const { limits, loading, error } = useLimitStatus();

  if (loading)
    return (
      <div className="d-flex align-items-center text-muted small">
        <Spinner size="sm" className="me-2" />
        <span>Limit bilgileri yükleniyor...</span>
      </div>
    );

  if (error || !limits)
    return (
      <div className="d-flex align-items-center text-danger small">
        <AlertTriangle size={16} className="me-2" />
        <span>Limit bilgileri alınamadı</span>
      </div>
    );

  const keys = Object.keys(limits);
  if (keys.length === 0) {
    return (
      <div className="d-flex align-items-center text-success small">
        <ShieldCheck size={16} className="me-2" />
        <span>Bu kullanıcı limitsizdir</span>
      </div>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {Object.entries(limits).map(([key, info]) => {
        const label = limitLabels[key] || key.replace(/_/g, ' ').toUpperCase();
        const progressColor =
          info.percent_used >= 90
            ? 'bg-danger'
            : info.percent_used >= 75
            ? 'bg-warning'
            : undefined;

        return (
          <Card key={key} className="shadow-sm border">
            <CardBody className="py-4">
              <div className="text-sm text-muted-foreground font-medium mb-1">
                {label}
              </div>
              <div className="d-flex justify-content-between text-xs mb-1">
                <span>Kullanım: {info.used} / {info.limit}</span>
                <span>{info.remaining} kaldı</span>
              </div>
              <Progress value={info.percent_used} className={progressColor} />
            </CardBody>
          </Card>
        );
      })}
    </div>
  );
}

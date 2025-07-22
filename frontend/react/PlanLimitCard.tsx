import React from 'react';
import useLimitStatus from './hooks/useLimitStatus';
import { Card, CardContent } from './components/ui/card';
import { Progress } from './components/ui/progress';
import { Loader2, AlertTriangle, ShieldCheck, Bell, BellRing } from 'lucide-react';

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
      <div className="flex items-center space-x-2 text-muted-foreground text-sm">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Limit bilgileri yükleniyor...</span>
      </div>
    );

  if (error || !limits)
    return (
      <div className="flex items-center space-x-2 text-red-500 text-sm">
        <AlertTriangle className="w-4 h-4" />
        <span>Limit bilgileri alınamadı</span>
      </div>
    );

  const keys = Object.keys(limits);
  if (keys.length === 0) {
    return (
      <div className="flex items-center space-x-2 text-green-600 text-sm">
        <ShieldCheck className="w-4 h-4" />
        <span>Bu kullanıcı limitsizdir</span>
      </div>
    );
  }

  return (
    <section className="space-y-2">
      <h3 className="text-base font-semibold text-muted-foreground">Kullanım Limitleri</h3>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {Object.entries(limits).map(([key, info]) => {
          const label = limitLabels[key] || key.replace(/_/g, ' ').toUpperCase();
          const progressColor =
            info.percent_used >= 100 ? 'bg-red-600'
            : info.percent_used >= 90 ? 'bg-red-500'
            : info.percent_used >= 75 ? 'bg-yellow-500'
            : undefined;

          const warningIcon =
            info.percent_used >= 100 ? (
              <BellRing className="w-4 h-4 text-red-600" title="Limit doldu" />
            ) : info.percent_used >= 90 ? (
              <Bell className="w-4 h-4 text-red-500" title="%90 kullanım" />
            ) : info.percent_used >= 75 ? (
              <Bell className="w-4 h-4 text-yellow-500" title="%75 kullanım" />
            ) : null;

          return (
            <Card key={key} className="shadow-sm border">
              <CardContent className="py-4">
                <div className="flex items-center justify-between mb-1">
                  <div className="text-sm text-muted-foreground font-medium">
                    {label}
                  </div>
                  {warningIcon && <div>{warningIcon}</div>}
                </div>
                <div className="flex justify-between text-xs mb-1">
                  <span>Kullanım: {info.used} / {info.limit}</span>
                  <span>{info.remaining} kaldı</span>
                </div>
                <Progress value={info.percent_used} className={progressColor} />
              </CardContent>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

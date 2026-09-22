"use client";

import { usePredictionAccuracy } from "@/hooks/prediction/usePredictionAccuracy";
import type { ComparisonPeriod } from "@/types/prediction";

type PredictionKpiRowProps = {
  siteId: string;
  period: ComparisonPeriod;
};

type Kpi = {
  label: string;
  value: string;
  hint: string;
};

const PERIOD_LABEL: Record<ComparisonPeriod, string> = {
  "24h": "les dernières 24h",
  "7d": "les 7 derniers jours",
};

function formatKw(value: number): string {
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} kW`;
}

function formatPercent(value: number): string {
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })}%`;
}

export function PredictionKpiRow({ siteId, period }: PredictionKpiRowProps) {
  const { maeKw, errorPct, accuracyPct } = usePredictionAccuracy(siteId, period);
  const periodLabel = PERIOD_LABEL[period];

  const kpis: Kpi[] = [
    {
      label: "Écart moyen (MAE)",
      value: maeKw !== null ? formatKw(maeKw) : "—",
      hint: `MAE glissante sur ${periodLabel}`,
    },
    {
      label: "Erreur moyenne",
      value: errorPct !== null ? formatPercent(errorPct) : "—",
      hint: `MAE / consommation moyenne (${period === "24h" ? "24h" : "7j"})`,
    },
    {
      label: "Précision du modèle",
      value: accuracyPct !== null ? formatPercent(accuracyPct) : "—",
      hint: "Horizon maximum : 7 jours",
    },
  ];

  return (
    <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
      {kpis.map((kpi) => (
        <div
          key={kpi.label}
          className="rounded-2xl bg-white p-5 shadow-sm"
          style={{ boxShadow: "var(--card-shadow)" }}
        >
          <p className="mb-2 text-xs font-medium text-zinc-500">{kpi.label}</p>
          <p className="text-2xl font-bold tracking-tight text-zinc-900">
            {kpi.value}
          </p>
          <p className="mt-1.5 text-xs text-zinc-400">{kpi.hint}</p>
        </div>
      ))}
    </div>
  );
}

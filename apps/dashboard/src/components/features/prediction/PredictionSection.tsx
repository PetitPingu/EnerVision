"use client";

import { EmptyState } from "@/components/EmptyState";
import { DriftBadge } from "@/components/features/prediction/DriftBadge";
import { PredictionComparisonChart } from "@/components/features/prediction/PredictionComparisonChart";
import { usePredictionComparison } from "@/hooks/prediction/usePredictionComparison";
import { useModelDrift } from "@/hooks/prediction/useModelDrift";
import type { ComparisonPeriod } from "@/types/prediction";

type PredictionSectionProps = {
  siteId: string;
  period: ComparisonPeriod;
  onPeriodChange: (period: ComparisonPeriod) => void;
};

const PERIOD_OPTIONS: { value: ComparisonPeriod; label: string }[] = [
  { value: "24h", label: "24h" },
  { value: "7d", label: "7 jours" },
];

function PeriodToggle({
  value,
  onChange,
}: {
  value: ComparisonPeriod;
  onChange: (period: ComparisonPeriod) => void;
}) {
  return (
    <div className="flex gap-1 rounded-[10px] bg-zinc-100 p-[3px]">
      {PERIOD_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          className={`rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-colors ${
            value === option.value
              ? "bg-white text-zinc-900 shadow-sm"
              : "text-zinc-500 hover:text-zinc-900"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function PredictionSection({
  siteId,
  period,
  onPeriodChange,
}: PredictionSectionProps) {
  const { data, nowBucket, isLoading, error } = usePredictionComparison(
    siteId,
    period,
  );
  const drift = useModelDrift(siteId);

  return (
    <div
      className="rounded-2xl bg-white p-8 shadow-sm"
      style={{ boxShadow: "var(--card-shadow)" }}
    >
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-xl font-semibold text-zinc-900">
              Consommation prévue vs réelle
            </h2>
            <DriftBadge drift={drift} />
          </div>
          <p className="mt-1 text-sm text-zinc-500">
            Historique mesuré et projection du modèle, sur le même graphique.
          </p>
        </div>
        <PeriodToggle value={period} onChange={onPeriodChange} />
      </div>

      {isLoading ? (
        <div className="h-[440px] animate-pulse rounded-xl bg-zinc-50" />
      ) : error ? (
        <p className="text-sm text-red-600">
          Impossible de charger la comparaison prévu / réel.
        </p>
      ) : data.length === 0 ? (
        <EmptyState message="Pas de donnée" />
      ) : (
        <PredictionComparisonChart
          data={data}
          nowBucket={nowBucket}
          maeByHorizon={drift?.mae_by_horizon ?? {}}
          fallbackMae={(period === "24h" ? drift?.mae_24h_kwh : drift?.mae_7d_kwh) ?? null}
        />
      )}
    </div>
  );
}

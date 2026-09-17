"use client";

import { useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { PredictionComparisonChart } from "@/components/features/prediction/PredictionComparisonChart";
import { usePredictionComparison } from "@/hooks/prediction/usePredictionComparison";
import type { ComparisonPeriod } from "@/types/prediction";

type PredictionSectionProps = {
  siteId: string;
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

export function PredictionSection({ siteId }: PredictionSectionProps) {
  const [period, setPeriod] = useState<ComparisonPeriod>("24h");
  const { data, nowBucket, isLoading, error } = usePredictionComparison(
    siteId,
    period,
  );

  return (
    <div
      className="rounded-2xl bg-white p-8 shadow-sm"
      style={{ boxShadow: "var(--card-shadow)" }}
    >
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-900">
            Consommation prévue vs réelle
          </h2>
          <p className="mt-1 text-sm text-zinc-500">
            Historique mesuré et projection du modèle, sur le même graphique.
          </p>
        </div>
        <PeriodToggle value={period} onChange={setPeriod} />
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
        <PredictionComparisonChart data={data} nowBucket={nowBucket} />
      )}
    </div>
  );
}

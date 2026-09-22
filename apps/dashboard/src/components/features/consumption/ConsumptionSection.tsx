"use client";

import { ConsumptionChart } from "@/components/features/consumption/ConsumptionChart";
import { EmptyState } from "@/components/EmptyState";
import { useConsumptionReadings } from "@/hooks/consumption/useConsumptionReadings";

type ConsumptionSectionProps = {
  siteId: string;
};

function LoadingSkeleton() {
  return (
    <div
      className="rounded-2xl bg-white p-6 shadow-sm"
      style={{ boxShadow: "var(--card-shadow)" }}
    >
      <div className="mb-6 space-y-2">
        <div className="h-5 w-48 animate-pulse rounded bg-zinc-100" />
        <div className="h-9 w-32 animate-pulse rounded bg-zinc-100" />
      </div>
      <div className="h-72 animate-pulse rounded-xl bg-zinc-50" />
    </div>
  );
}

export function ConsumptionSection({ siteId }: ConsumptionSectionProps) {
  const { data, isLoading, error } = useConsumptionReadings(siteId);

  if (isLoading) {
    return <LoadingSkeleton />;
  }

  if (error) {
    return (
      <div
        className="rounded-2xl bg-white p-6 shadow-sm"
        style={{ boxShadow: "var(--card-shadow)" }}
      >
        <p className="text-sm text-red-600">
          Impossible de charger les données de consommation.
        </p>
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div
        className="rounded-2xl bg-white p-6 shadow-sm"
        style={{ boxShadow: "var(--card-shadow)" }}
      >
        <h2 className="mb-4 text-lg font-semibold text-zinc-900">
          Consommation en temps réel
        </h2>
        <EmptyState message="Pas de donnée" />
      </div>
    );
  }

  return <ConsumptionChart data={data} />;
}

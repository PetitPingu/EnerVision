"use client";

import { useMemo, useState } from "react";
import { EmptyState } from "@/components/EmptyState";
import { SensorStateGrid } from "@/components/features/prediction/SensorStateGrid";
import { useSensorStatePrediction } from "@/hooks/prediction/useSensorStatePrediction";

type SensorPredictionSectionProps = {
  siteId: string;
};

/** Arrondit à l'heure suivante : le modèle d'état prédit à l'heure/minute
 * près, une prévision "à la prochaine heure" est la plus utile par défaut. */
function nextHourIso(): string {
  const date = new Date();
  date.setMinutes(0, 0, 0);
  date.setHours(date.getHours() + 1);
  return date.toISOString();
}

/** Format attendu par <input type="datetime-local">, en heure locale. */
function toDatetimeLocalValue(iso: string): string {
  const date = new Date(iso);
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

export function SensorPredictionSection({ siteId }: SensorPredictionSectionProps) {
  const [targetTimestamp, setTargetTimestamp] = useState(nextHourIso);
  const { data, isLoading, modelNotLoaded, error } = useSensorStatePrediction(
    siteId,
    targetTimestamp,
  );

  const formattedTarget = useMemo(() => {
    try {
      return new Date(targetTimestamp).toLocaleString("fr-FR", {
        dateStyle: "medium",
        timeStyle: "short",
      });
    } catch {
      return targetTimestamp;
    }
  }, [targetTimestamp]);

  return (
    <div
      className="rounded-2xl bg-white p-8 shadow-sm"
      style={{ boxShadow: "var(--card-shadow)" }}
    >
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold text-zinc-900">
            État prédit des capteurs
          </h2>
          <p className="mt-1 text-sm text-zinc-500">
            Prévision pour le {formattedTarget}
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm text-zinc-600">
          Instant cible
          <input
            type="datetime-local"
            className="rounded-lg border border-zinc-200 px-2.5 py-1.5 text-sm text-zinc-700"
            value={toDatetimeLocalValue(targetTimestamp)}
            onChange={(event) => {
              const value = event.target.value;
              if (value) {
                setTargetTimestamp(new Date(value).toISOString());
              }
            }}
          />
        </label>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {[0, 1, 2, 3, 4, 5].map((key) => (
            <div key={key} className="h-14 animate-pulse rounded-xl bg-zinc-50" />
          ))}
        </div>
      ) : modelNotLoaded ? (
        <EmptyState message="Aucun modèle d'état des capteurs n'a encore été entraîné" />
      ) : error ? (
        <p className="text-sm text-red-600">
          Impossible de charger l&apos;état prédit des capteurs.
        </p>
      ) : data ? (
        <>
          <SensorStateGrid sensors={data.sensors} />
          <p className="mt-4 text-xs text-zinc-400">
            Modèle {data.model_version}
          </p>
        </>
      ) : (
        <EmptyState message="Pas de prévision disponible pour ce site" />
      )}
    </div>
  );
}

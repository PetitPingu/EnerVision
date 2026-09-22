"use client";

import { useState } from "react";
import { SensorForecastTimeline } from "@/components/features/sites/SensorForecastTimeline";
import { DATA_QUALITY_LABELS, DATA_QUALITY_PILL_STYLES } from "@/lib/format/dataQuality";
import { deriveSensorCategoryStatus } from "@/lib/format/sensorCategory";
import type { ConsumptionReading } from "@/types/consumption";
import type { Site } from "@/types/site";

const SENSOR_LABELS: Record<string, string> = {
  consumption: "Consommation",
  electrical: "Électrique",
  temperature: "Température",
  humidity: "Humidité",
};

type SiteSensorsModalProps = {
  site: Site;
  /** Dernière lecture connue du site (readings_curated), fournie par le
   * parent (SiteCard) — polling partagé, pas un fetch propre à la modale. */
  reading: ConsumptionReading | undefined;
  onClose: () => void;
};

export function SiteSensorsModal({ site, reading, onClose }: SiteSensorsModalProps) {
  const [expandedSensor, setExpandedSensor] = useState<string | null>(null);

  // État de chaque catégorie déduit de la dernière lecture de notre base
  // (ce qu'etl_worker y écrit chaque minute), pas d'un appel séparé à
  // l'état "en direct" de l'API mock — voir deriveSensorCategoryStatus.
  const categoryStatus = deriveSensorCategoryStatus(reading ?? null);
  const sensors = Object.entries(categoryStatus);
  // Capteurs en panne d'abord, pour attirer l'œil sur ce qui compte.
  const sortedSensors = [...sensors].sort(([, a], [, b]) => {
    if (a === b) return 0;
    return a === "failing" ? -1 : 1;
  });

  const dataQuality = reading?.data_quality ?? "good";
  const overallLabel = DATA_QUALITY_LABELS[dataQuality];
  const pillStyle = DATA_QUALITY_PILL_STYLES[dataQuality];

  function togglePrediction(sensorName: string) {
    setExpandedSensor((current) => (current === sensorName ? null : sensorName));
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 px-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-label={`Capteurs · ${site.site_name ?? site.site_id}`}
        className="w-full max-w-md rounded-2xl border border-zinc-200 bg-white p-6 shadow-lg"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-zinc-400">
              {site.site_id}
            </p>
            <h2 className="text-lg font-semibold text-zinc-900">
              Capteurs · {site.site_name ?? site.site_id}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Fermer"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-zinc-400 transition-colors hover:bg-zinc-100 hover:text-zinc-700"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden="true">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <p className="mt-1 text-sm text-blue-600">
          État des capteurs · {site.site_name ?? site.site_id}
        </p>

        {!reading ? (
          <p className="mt-4 text-sm text-zinc-500">
            État des capteurs indisponible pour ce site.
          </p>
        ) : (
          <ul className="mt-4 divide-y divide-zinc-100 rounded-xl border border-zinc-100">
            {sortedSensors.map(([name, sensorStatus]) => {
              const sensorLabel = SENSOR_LABELS[name] ?? name;
              const isFailing = sensorStatus === "failing";

              return (
                <li key={name} className="px-3 py-2.5">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span
                        className={`h-2 w-2 shrink-0 rounded-full ${
                          isFailing ? "bg-red-500" : "bg-emerald-500"
                        }`}
                        aria-hidden="true"
                      />
                      <span className="text-sm text-zinc-700">Capteur {sensorLabel}</span>
                    </div>
                    <span className="text-xs text-zinc-400">
                      {isFailing ? "En panne" : "OK"}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => togglePrediction(name)}
                    className="mt-1.5 text-xs font-medium text-zinc-600 transition-colors hover:text-zinc-900"
                  >
                    {expandedSensor === name
                      ? "Masquer la prédiction"
                      : "Faire la prédiction pour ce capteur →"}
                  </button>

                  {expandedSensor === name && (
                    <SensorForecastTimeline
                      siteId={site.site_id}
                      sensorCategory={name}
                      sensorLabel={sensorLabel}
                      siteName={site.site_name ?? site.site_id}
                    />
                  )}
                </li>
              );
            })}
          </ul>
        )}

        <div
          className={`mt-4 inline-flex items-center rounded-full border px-3 py-1.5 text-sm font-medium ${pillStyle}`}
        >
          État du site : actuellement {overallLabel}
        </div>
      </div>
    </div>
  );
}

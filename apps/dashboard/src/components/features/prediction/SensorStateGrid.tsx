import type { SensorOnOffState } from "@/types/sensors";

type SensorStateGridProps = {
  sensors: Record<string, SensorOnOffState>;
};

// Ordre et libellés alignés sur SENSOR_COLUMNS
// (apps/prediction/infrastructure/ml/state/features.py).
const SENSOR_LABELS: Record<string, string> = {
  consumption_kw: "Consommation",
  voltage_v: "Tension",
  current_a: "Courant",
  power_factor: "Facteur de puissance",
  temperature_celsius: "Température",
  humidity_percent: "Humidité",
};

const SENSOR_ORDER = Object.keys(SENSOR_LABELS);

export function SensorStateGrid({ sensors }: SensorStateGridProps) {
  const entries = SENSOR_ORDER.filter((key) => key in sensors).map(
    (key) => [key, sensors[key]] as const,
  );

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
      {entries.map(([key, state]) => (
        <div
          key={key}
          className="flex items-center justify-between rounded-xl border border-zinc-100 bg-zinc-50 px-4 py-3"
        >
          <span className="text-sm font-medium text-zinc-700">
            {SENSOR_LABELS[key] ?? key}
          </span>
          <span
            className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
              state === "on"
                ? "bg-emerald-50 text-emerald-700"
                : "bg-red-50 text-red-700"
            }`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {state === "on" ? "En marche" : "En panne"}
          </span>
        </div>
      ))}
    </div>
  );
}

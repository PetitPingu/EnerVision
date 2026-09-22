import type { DriftStatus, ModelDrift } from "@/types/model-health";

// Seuils documentés dans docs/monitoring_model.md (cohérents avec
// apps/core_api/presentation/api.py, DRIFT_MODERATE_THRESHOLD / DRIFT_CRITICAL_THRESHOLD).
const STATUS_STYLES: Record<DriftStatus, string> = {
  stable: "bg-emerald-50 text-emerald-700",
  moderate: "bg-amber-50 text-amber-700",
  critical: "bg-red-50 text-red-700",
  unknown: "bg-zinc-100 text-zinc-500",
};

const STATUS_LABELS: Record<DriftStatus, string> = {
  stable: "Modèle stable",
  moderate: "Dérive modérée",
  critical: "Dérive critique",
  unknown: "Drift indisponible",
};

type DriftBadgeProps = {
  drift: ModelDrift | null;
};

export function DriftBadge({ drift }: DriftBadgeProps) {
  const status = drift?.status ?? "unknown";
  const score = drift?.drift_score;

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold ${STATUS_STYLES[status]}`}
      title="Score de drift : écart de distribution de consumption_kwh vs la fenêtre d'entraînement du modèle (docs/monitoring_model.md)."
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {STATUS_LABELS[status]}
      {score !== null && score !== undefined ? ` (${score.toFixed(1)})` : ""}
    </span>
  );
}

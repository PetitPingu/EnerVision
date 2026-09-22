/**
 * PLACEHOLDER — pas de backend réel derrière ce composant.
 *
 * Aucun service ne prédit aujourd'hui un état de capteur (partiel/dégradé/
 * critique) à l'heure ni un score de confiance : le service prediction ne
 * fait que de la régression sur la consommation (kWh), voir
 * apps/prediction/presentation/api.py (/predict, /predict/range).
 *
 * À remplacer par un vrai appel API quand ce modèle existera. En attendant,
 * les valeurs ci-dessous sont statiques, uniquement pour caler la mise en
 * page — HOURS/CONFIDENCE ne reflètent rien de réel.
 */
type HourSeverity = "partiel" | "degrade" | "critique";

const HOURS: HourSeverity[] = [
  "partiel", "partiel", "partiel", "partiel", "partiel", "partiel", "partiel", "partiel",
  "degrade", "degrade", "degrade", "degrade", "degrade", "degrade", "degrade", "degrade",
  "critique", "critique", "critique", "critique", "critique", "critique", "critique", "critique",
];

const PLACEHOLDER_CONFIDENCE = 78;
const PLACEHOLDER_FORECAST_AT_24H: HourSeverity = "critique";

const SEVERITY_LABELS: Record<HourSeverity, string> = {
  partiel: "Partiel",
  degrade: "Dégradé",
  critique: "Critique",
};

const SEVERITY_BAR_COLORS: Record<HourSeverity, string> = {
  partiel: "bg-blue-500",
  degrade: "bg-amber-500",
  critique: "bg-red-500",
};

const SEVERITY_PILL_STYLES: Record<HourSeverity, string> = {
  partiel: "bg-blue-50 text-blue-700",
  degrade: "bg-amber-50 text-amber-700",
  critique: "bg-red-50 text-red-700",
};

type SensorPredictionPlaceholderProps = {
  sensorLabel: string;
  siteName: string;
};

export function SensorPredictionPlaceholder({
  sensorLabel,
  siteName,
}: SensorPredictionPlaceholderProps) {
  return (
    <div className="mt-3 border-t border-zinc-100 pt-3">
      <p className="text-xs font-medium text-zinc-500">
        Prédiction des états des capteurs · {sensorLabel} ({siteName}) — 24 prochaines heures
      </p>

      <div
        className={`mt-2 inline-flex items-center rounded-lg px-2.5 py-1 text-xs font-medium ${SEVERITY_PILL_STYLES[PLACEHOLDER_FORECAST_AT_24H]}`}
      >
        Prévu à 24h : {SEVERITY_LABELS[PLACEHOLDER_FORECAST_AT_24H]}
      </div>

      <p className="mt-2 text-xs text-zinc-400">
        Confiance du modèle : {PLACEHOLDER_CONFIDENCE}%
      </p>

      <div className="mt-2 flex gap-0.5" aria-hidden="true">
        {HOURS.map((severity, index) => (
          <span
            key={index}
            title={`H+${index + 1} : ${SEVERITY_LABELS[severity]}`}
            className={`h-6 flex-1 rounded-sm ${SEVERITY_BAR_COLORS[severity]}`}
          />
        ))}
      </div>
      <div className="mt-1 flex justify-between text-[10px] text-zinc-400">
        <span>H+1</span>
        <span>H+24</span>
      </div>
    </div>
  );
}

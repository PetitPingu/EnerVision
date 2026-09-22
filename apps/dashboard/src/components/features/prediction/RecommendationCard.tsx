import type { Recommendation, RecommendationAction } from "@/types/recommendation";

type Priority = "haute" | "moyenne";

type ActionMeta = {
  title: string;
  priority: Priority;
  icon: React.ReactNode;
};

const PRIORITY_STYLES: Record<Priority, string> = {
  haute: "bg-red-50 text-red-700",
  moyenne: "bg-amber-50 text-amber-700",
};

const PRIORITY_LABELS: Record<Priority, string> = {
  haute: "Priorité haute",
  moyenne: "Priorité moyenne",
};

function BoltIcon() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.75}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z"
      />
    </svg>
  );
}

function ClockArrowIcon() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.75}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 6v6l4 2m5-2a9 9 0 11-18 0 9 9 0 0118 0z"
      />
    </svg>
  );
}

function WarningTriangleIcon() {
  return (
    <svg
      className="h-5 w-5"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={1.75}
      aria-hidden="true"
    >
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"
      />
    </svg>
  );
}

// Le service recommendation ne renvoie ni titre court, ni priorité (seul un
// `action` + une justification en phrase complète) — ce mapping fixe les
// deux côté dashboard, par type de règle métier (cf. rules_engine.py) :
// load_shifting et peak_shift répondent à un risque de dépassement /
// tarif de pointe (haute), power_factor_compensation à un risque de
// pénalité, moins immédiat (moyenne).
const ACTION_META: Record<RecommendationAction, ActionMeta> = {
  load_shifting: {
    title: "Décaler la charge du site",
    priority: "haute",
    icon: <BoltIcon />,
  },
  peak_shift: {
    title: "Reporter la consommation hors pointe",
    priority: "haute",
    icon: <ClockArrowIcon />,
  },
  power_factor_compensation: {
    title: "Vérifier le facteur de puissance du site",
    priority: "moyenne",
    icon: <WarningTriangleIcon />,
  },
};

function formatGain(gainKwh: number): string {
  const rounded = Math.round(gainKwh * 10) / 10;
  return `-${rounded.toLocaleString("fr-FR")} kWh estimés`;
}

type RecommendationCardProps = {
  recommendation: Recommendation;
};

export function RecommendationCard({ recommendation }: RecommendationCardProps) {
  const meta = ACTION_META[recommendation.action];

  return (
    <div
      className="rounded-2xl bg-white p-5 shadow-sm"
      style={{ boxShadow: "var(--card-shadow)" }}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-zinc-900 text-white">
            {meta.icon}
          </div>
          <h3 className="pt-1.5 text-sm font-semibold text-zinc-900">
            {meta.title}
          </h3>
        </div>
        <span
          className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${PRIORITY_STYLES[meta.priority]}`}
        >
          {PRIORITY_LABELS[meta.priority]}
        </span>
      </div>

      <p className="text-sm text-zinc-500">{recommendation.justification}</p>

      {recommendation.estimated_gain_kwh !== null && (
        <span className="mt-3 inline-block rounded-full bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
          {formatGain(recommendation.estimated_gain_kwh)}
        </span>
      )}
    </div>
  );
}

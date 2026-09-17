type Kpi = {
  label: string;
  value: string;
  hint: string;
  hintClassName?: string;
};

// Valeurs mockées : le calcul réel (MAE, précision du modèle) n'est pas
// dans le périmètre du ticket #92, qui ne porte que sur le graphique.
const KPIS: Kpi[] = [
  { label: "Écart moyen (MAE)", value: "4,8 kW", hint: "Sur la période affichée" },
  {
    label: "Erreur moyenne",
    value: "3,1%",
    hint: "-0,4 pt vs semaine dernière",
    hintClassName: "text-green-600",
  },
  {
    label: "Précision du modèle",
    value: "94%",
    hint: "Horizon maximum : 7 jours",
  },
];

export function PredictionKpiRow() {
  return (
    <div className="mb-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
      {KPIS.map((kpi) => (
        <div
          key={kpi.label}
          className="rounded-2xl bg-white p-5 shadow-sm"
          style={{ boxShadow: "var(--card-shadow)" }}
        >
          <p className="mb-2 text-xs font-medium text-zinc-500">{kpi.label}</p>
          <p className="text-2xl font-bold tracking-tight text-zinc-900">
            {kpi.value}
          </p>
          <p className={`mt-1.5 text-xs ${kpi.hintClassName ?? "text-zinc-400"}`}>
            {kpi.hint}
          </p>
        </div>
      ))}
    </div>
  );
}

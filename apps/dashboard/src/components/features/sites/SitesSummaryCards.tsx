type SitesSummaryCardsProps = {
  sitesCount: number;
  sensorsOnCount: number;
  sensorsOffCount: number;
};

export function SitesSummaryCards({
  sitesCount,
  sensorsOnCount,
  sensorsOffCount,
}: SitesSummaryCardsProps) {
  const total = sensorsOnCount + sensorsOffCount;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
      <div
        className="rounded-2xl bg-white p-6 shadow-sm"
        style={{ boxShadow: "var(--card-shadow)" }}
      >
        <p className="text-sm text-zinc-500">Sites suivis</p>
        <p className="mt-2 text-3xl font-semibold text-zinc-900">{sitesCount}</p>
      </div>

      <div className="rounded-2xl bg-zinc-900 p-6 text-white shadow-sm">
        <p className="text-sm text-zinc-400">Capteurs — tous les sites</p>
        <p className="mt-2 text-3xl font-semibold">
          {total} <span className="text-base font-normal text-zinc-400">au total</span>
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-4 text-sm text-zinc-300">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            {sensorsOnCount} en marche
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-red-500" />
            {sensorsOffCount} en panne
          </span>
        </div>
      </div>
    </div>
  );
}

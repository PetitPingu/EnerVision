"use client";

import { useSiteSelection } from "@/contexts/SiteSelectionContext";

function formatSiteLabel(site: {
  site_id: string;
  site_name: string | null;
}): string {
  const label = site.site_name ?? site.site_id;
  return `${site.site_id} - ${label}`;
}

export function SiteSelect() {
  const { sites, selectedSiteId, setSelectedSiteId, isLoading, error } =
    useSiteSelection();

  if (error) {
    return (
      <span className="text-sm text-red-600">Sites indisponibles</span>
    );
  }

  return (
    <label className="relative">
      <span className="sr-only">Sélectionner un site</span>
      <select
        value={selectedSiteId}
        onChange={(event) => setSelectedSiteId(event.target.value)}
        disabled={isLoading || sites.length === 0}
        className="h-10 min-w-[16rem] appearance-none rounded-xl border border-zinc-200 bg-white py-2 pl-3 pr-9 text-sm font-medium text-zinc-900 transition-colors hover:bg-zinc-50 focus:border-zinc-300 focus:outline-none focus:ring-2 focus:ring-zinc-200 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isLoading ? (
          <option value={selectedSiteId}>Chargement…</option>
        ) : (
          sites.map((site) => (
            <option key={site.site_id} value={site.site_id}>
              {formatSiteLabel(site)}
            </option>
          ))
        )}
      </select>
      <svg
        className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-400"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
        aria-hidden="true"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
      </svg>
    </label>
  );
}

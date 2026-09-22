export const SITE_TYPE_LABELS: Record<string, string> = {
  office: "Bureau",
  factory: "Usine",
  datacenter: "Data center",
  retail: "Commerce",
  hospital: "Hôpital",
};

export function formatSiteSubtitle(site: {
  site_name: string | null;
  site_type: string | null;
  location: string | null;
}): string {
  const typeLabel =
    (site.site_type && SITE_TYPE_LABELS[site.site_type]) ?? site.site_type;

  if (site.site_name && typeLabel && site.location) {
    return `${site.site_name} — ${typeLabel} · ${site.location}`;
  }

  if (site.site_name && site.location) {
    return `${site.site_name} — ${site.location}`;
  }

  return site.site_name ?? "Site sélectionné";
}

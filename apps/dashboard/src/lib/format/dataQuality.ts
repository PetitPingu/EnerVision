import type { DataQuality } from "@/types/consumption";

/** Palette unique pour data_quality, réutilisée partout où l'état d'un
 * site/capteur s'affiche (pastilles des cartes, pastille "État du site" de
 * la modale) : good < partial < degraded < critical, une couleur par
 * palier, jamais recalculée différemment d'un endroit à l'autre. */
export const DATA_QUALITY_LABELS: Record<DataQuality, string> = {
  good: "normal",
  partial: "partiel",
  degraded: "dégradé",
  critical: "critique",
};

export const DATA_QUALITY_DOT_COLORS: Record<DataQuality, string> = {
  good: "bg-emerald-500",
  partial: "bg-blue-500",
  degraded: "bg-amber-500",
  critical: "bg-red-500",
};

export const DATA_QUALITY_PILL_STYLES: Record<DataQuality, string> = {
  good: "border-emerald-200 text-emerald-700",
  partial: "border-blue-200 text-blue-700",
  degraded: "border-amber-200 text-amber-700",
  critical: "border-red-200 text-red-700",
};

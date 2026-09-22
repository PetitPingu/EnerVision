"use client";

import { EmptyState } from "@/components/EmptyState";
import { RecommendationCard } from "@/components/features/prediction/RecommendationCard";
import { useRecommendations } from "@/hooks/recommendation/useRecommendations";

type RecommendationsSectionProps = {
  siteId: string;
};

export function RecommendationsSection({ siteId }: RecommendationsSectionProps) {
  const { data, isLoading, error } = useRecommendations(siteId);

  return (
    <div
      className="mt-6 rounded-2xl bg-white p-8 shadow-sm"
      style={{ boxShadow: "var(--card-shadow)" }}
    >
      <div className="mb-6 flex items-start justify-between gap-4">
        <h2 className="text-xl font-semibold text-zinc-900">
          Recommandations actives
        </h2>
        {!isLoading && !error && data.length > 0 && (
          <p className="pt-1 text-sm text-zinc-500">
            {data.length} recommandation{data.length > 1 ? "s" : ""} générée
            {data.length > 1 ? "s" : ""} à partir de la prévision
          </p>
        )}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {[0, 1].map((key) => (
            <div
              key={key}
              className="h-32 animate-pulse rounded-2xl bg-zinc-50"
            />
          ))}
        </div>
      ) : error ? (
        <p className="text-sm text-red-600">
          Impossible de charger les recommandations.
        </p>
      ) : data.length === 0 ? (
        <EmptyState message="Aucune recommandation active pour ce site" />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {data.map((recommendation, index) => (
            <RecommendationCard
              // L'API ne renvoie pas d'identifiant propre à la recommandation
              // (seule la ligne DB a un id, non exposé) : (site_id, action)
              // n'est pas garanti unique si une même règle se déclenche deux
              // fois pour des raisons différentes, d'où l'index en repli.
              key={`${recommendation.site_id}-${recommendation.action}-${index}`}
              recommendation={recommendation}
            />
          ))}
        </div>
      )}
    </div>
  );
}

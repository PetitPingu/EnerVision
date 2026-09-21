"use client";

import { useAuth } from "@/contexts/AuthContext";

type AuthGateProps = {
  children: React.ReactNode;
};

/**
 * N'affiche le contenu (et ne monte les hooks de données qu'il contient)
 * qu'une fois connecté — sinon chaque hook (useConsumptionReadings,
 * usePredictionComparison, useRecommendations, ...) tenterait un appel
 * API voué au 401 avant que le JWT n'existe.
 */
export function AuthGate({ children }: AuthGateProps) {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) return null;

  if (!isAuthenticated) {
    return (
      <main className="flex flex-1 items-center justify-center px-6 py-8">
        <p className="text-sm text-zinc-500">
          Connectez-vous pour accéder aux données du dashboard.
        </p>
      </main>
    );
  }

  return <>{children}</>;
}

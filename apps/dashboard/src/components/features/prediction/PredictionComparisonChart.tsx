"use client";

import { useMemo } from "react";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ComparisonPoint } from "@/hooks/prediction/usePredictionComparison";

type PredictionComparisonChartProps = {
  data: ComparisonPoint[];
  /** Bucket (clé ISO unique) du point de jonction — voir usePredictionComparison. */
  nowBucket: string | null;
};

function formatKw(value: number): string {
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} kW`;
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: ComparisonPoint }>;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  const point = payload[0].payload;

  return (
    <div className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs shadow-sm">
      <p className="font-medium text-zinc-700">{point.label}</p>
      <p className="text-zinc-500">
        Mesurée : {point.actual_kw !== null ? formatKw(point.actual_kw) : "—"}
      </p>
      <p className="text-zinc-500">
        Prévue :{" "}
        {point.predicted_kw !== null ? formatKw(point.predicted_kw) : "—"}
      </p>
    </div>
  );
}

export function PredictionComparisonChart({
  data,
  nowBucket,
}: PredictionComparisonChartProps) {
  // Le libellé affiché ("14:00", "17/09 06h"...) peut être partagé par deux
  // buckets distincts (ex. début et fin d'une fenêtre 24h) : on affiche
  // toujours ce texte sur les ticks, mais on utilise le bucket (clé ISO
  // unique) comme dataKey réel de l'axe pour que recharts puisse toujours
  // positionner la ligne "Maintenant" sans ambiguïté.
  const labelByBucket = useMemo(
    () => new Map(data.map((point) => [point.bucket, point.label])),
    [data],
  );

  return (
    <div>
      <div className="h-[440px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={data}
            margin={{ top: 28, right: 16, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="predictionAreaFill" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor="var(--chart-primary)"
                  stopOpacity={0.3}
                />
                <stop
                  offset="100%"
                  stopColor="var(--chart-gradient-end)"
                  stopOpacity={0.03}
                />
              </linearGradient>
            </defs>

            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f4f4f5" />
            <XAxis
              dataKey="bucket"
              tickFormatter={(bucket: string) => labelByBucket.get(bucket) ?? bucket}
              tick={{ fill: "#a1a1aa", fontSize: 12.5 }}
              tickLine={false}
              axisLine={false}
              minTickGap={32}
            />
            <YAxis
              tick={{ fill: "#a1a1aa", fontSize: 12.5 }}
              tickLine={false}
              axisLine={false}
              width={52}
              label={{
                value: "kW",
                angle: -90,
                position: "insideLeft",
                fill: "#a1a1aa",
                fontSize: 12.5,
              }}
            />
            <Tooltip content={<ChartTooltip />} />

            <Area
              type="monotone"
              dataKey="actual_kw"
              stroke="none"
              fill="url(#predictionAreaFill)"
              connectNulls={false}
              isAnimationActive={false}
            />

            <Line
              type="monotone"
              dataKey="actual_kw"
              name="Consommation mesurée"
              stroke="var(--chart-primary)"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls={false}
            />
            <Line
              type="monotone"
              dataKey="predicted_kw"
              name="Prévision du modèle"
              stroke="var(--chart-primary)"
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4 }}
              connectNulls={false}
            />

            {nowBucket && (
              <ReferenceLine
                x={nowBucket}
                ifOverflow="visible"
                stroke="#a1a1aa"
                strokeWidth={1.5}
                strokeDasharray="3 4"
                label={{
                  value: "Maintenant",
                  position: "top",
                  fill: "#52525b",
                  fontSize: 12.5,
                  fontWeight: 600,
                }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 flex items-center gap-8 border-t border-zinc-100 pt-4">
        <div className="flex items-center gap-2 text-sm font-medium text-zinc-600">
          <span className="h-1 w-6 rounded-sm bg-[var(--chart-primary)]" />
          Consommation mesurée
        </div>
        <div className="flex items-center gap-2 text-sm font-medium text-zinc-600">
          <svg width="24" height="10" viewBox="0 0 24 10">
            <line
              x1="0"
              y1="5"
              x2="24"
              y2="5"
              stroke="var(--chart-primary)"
              strokeWidth={2.5}
            />
          </svg>
          Prévision du modèle
        </div>
      </div>
    </div>
  );
}

"use client";

import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ConsumptionReading } from "@/types/consumption";

type ChartPoint = {
  timestamp: string;
  consumption_kw: number | null;
  label: string;
};

type ConsumptionChartProps = {
  data: ConsumptionReading[];
};

function formatTime(timestamp: string): string {
  return new Date(timestamp).toLocaleTimeString("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatKw(value: number): string {
  return `${value.toLocaleString("fr-FR", { maximumFractionDigits: 1 })} kW`;
}

function getLatestConsumption(readings: ConsumptionReading[]): number | null {
  const sorted = [...readings].sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
  );

  for (const reading of sorted) {
    if (reading.consumption_kw !== null) {
      return reading.consumption_kw;
    }
  }

  return null;
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: ChartPoint }>;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  const point = payload[0].payload;
  const value = point.consumption_kw;

  return (
    <div className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-xs shadow-sm">
      <p className="font-medium text-zinc-700">{point.label}</p>
      <p className="text-zinc-500">
        {value !== null ? formatKw(value) : "Indisponible"}
      </p>
    </div>
  );
}

export function ConsumptionChart({ data }: ConsumptionChartProps) {
  const chartData = useMemo<ChartPoint[]>(
    () =>
      data
        .slice()
        .sort(
          (a, b) =>
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime(),
        )
        .map((reading) => ({
          timestamp: reading.timestamp,
          consumption_kw: reading.consumption_kw,
          label: formatTime(reading.timestamp),
        })),
    [data],
  );

  const latestConsumption = useMemo(() => getLatestConsumption(data), [data]);

  return (
    <div
      className="rounded-2xl bg-white p-6 shadow-sm"
      style={{ boxShadow: "var(--card-shadow)" }}
    >
      <div className="mb-6">
        <h2 className="text-lg font-semibold text-zinc-900">
          Consommation en temps réel
        </h2>
        {latestConsumption !== null && (
          <p className="mt-1 text-3xl font-bold tracking-tight text-zinc-900">
            {formatKw(latestConsumption)}
          </p>
        )}
      </div>

      <div className="h-72 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={chartData}
            margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
          >
            <defs>
              <linearGradient id="consumptionGradient" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor="var(--chart-primary)"
                  stopOpacity={0.35}
                />
                <stop
                  offset="100%"
                  stopColor="var(--chart-gradient-end)"
                  stopOpacity={0.05}
                />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              vertical={false}
              stroke="#f4f4f5"
            />
            <XAxis
              dataKey="label"
              tick={{ fill: "#a1a1aa", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              minTickGap={32}
            />
            <YAxis
              tick={{ fill: "#a1a1aa", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={48}
              tickFormatter={(value: number) => `${value}`}
              label={{
                value: "kW",
                angle: -90,
                position: "insideLeft",
                fill: "#a1a1aa",
                fontSize: 11,
              }}
            />
            <Tooltip content={<ChartTooltip />} />
            <Area
              type="monotone"
              dataKey="consumption_kw"
              stroke="var(--chart-primary)"
              strokeWidth={2}
              fill="url(#consumptionGradient)"
              connectNulls={false}
              dot={false}
              activeDot={{ r: 4, fill: "var(--chart-primary)" }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

type EnerVisionLogoProps = {
  size?: "sm" | "md";
};

export function EnerVisionLogo({ size = "md" }: EnerVisionLogoProps) {
  const dimensions = size === "sm" ? "h-8 w-8" : "h-11 w-11";
  const iconSize = size === "sm" ? "h-4 w-4" : "h-6 w-6";

  return (
    <div
      className={`flex ${dimensions} items-center justify-center rounded-lg bg-zinc-900 text-white`}
      aria-hidden="true"
    >
      <svg
        className={iconSize}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M13 2L3 14h8l-1 8 10-12h-8l1-8z"
        />
      </svg>
    </div>
  );
}

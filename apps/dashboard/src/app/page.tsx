import { ConsumptionSection } from "@/components/features/consumption/ConsumptionSection";
import { DEFAULT_SITE_ID } from "@/config/site";

export default function Home() {
  return (
    <main className="flex-1 px-6 py-8 lg:px-10 lg:py-10">
      <p className="mb-6 text-sm text-zinc-500">
        Site {DEFAULT_SITE_ID} — Bureau
      </p>

      <ConsumptionSection siteId={DEFAULT_SITE_ID} />
    </main>
  );
}

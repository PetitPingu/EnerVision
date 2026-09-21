"use client";

import { usePathname } from "next/navigation";
import { EnerVisionLogo } from "@/components/layout/EnerVisionLogo";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { SiteSelect } from "@/components/layout/SiteSelect";
import { NAV_ITEMS } from "@/config/navigation";
import { MOCK_USER } from "@/config/user";

function getPageTitle(pathname: string): string {
  const item = NAV_ITEMS.find((navItem) =>
    navItem.href === "/" ? pathname === "/" : pathname.startsWith(navItem.href),
  );

  return item?.label ?? "Dashboard";
}

function UserMenu() {
  return (
    <button
      type="button"
      aria-label="Menu utilisateur"
      className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-white px-3 py-2 transition-colors hover:bg-zinc-50"
    >
      <div
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-xs font-semibold text-zinc-600"
        aria-hidden="true"
      >
        {MOCK_USER.initials}
      </div>
      <div className="hidden text-left sm:block">
        <p className="text-sm font-semibold leading-tight text-zinc-900">
          {MOCK_USER.name}
        </p>
        <p className="text-xs text-zinc-500">{MOCK_USER.email}</p>
      </div>
      <svg
        className="hidden h-4 w-4 text-zinc-400 sm:block"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
        aria-hidden="true"
      >
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
      </svg>
    </button>
  );
}

export function TopHeader() {
  const pathname = usePathname();
  const pageTitle = getPageTitle(pathname);

  return (
    <header
      className="flex shrink-0 items-center justify-between border-b border-zinc-200/80 bg-zinc-50 px-6 py-4 lg:px-10"
    >
      <div className="flex items-center gap-4">
        <EnerVisionLogo size="sm" />
        <h1 className="text-lg font-semibold text-zinc-900">{pageTitle}</h1>
        <SiteSelect />
      </div>

      <div className="flex items-center gap-3">
        <NotificationBell />
        <UserMenu />
      </div>
    </header>
  );
}

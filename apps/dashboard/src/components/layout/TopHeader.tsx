"use client";

import { useState } from "react";
import { usePathname } from "next/navigation";
import { EnerVisionLogo } from "@/components/layout/EnerVisionLogo";
import { LoginButton } from "@/components/layout/LoginButton";
import { NotificationBell } from "@/components/layout/NotificationBell";
import { SiteSelect } from "@/components/layout/SiteSelect";
import { NAV_ITEMS } from "@/config/navigation";
import { useAuth } from "@/contexts/AuthContext";

function getPageTitle(pathname: string): string {
  const item = NAV_ITEMS.find((navItem) =>
    navItem.href === "/" ? pathname === "/" : pathname.startsWith(navItem.href),
  );

  return item?.label ?? "Dashboard";
}

function UserMenu({ email }: { email: string }) {
  const { logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const initials = email.slice(0, 2).toUpperCase();

  return (
    <div className="relative">
      <button
        type="button"
        aria-label="Menu utilisateur"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
        className="flex items-center gap-3 rounded-xl border border-zinc-200 bg-white px-3 py-2 transition-colors hover:bg-zinc-50"
      >
        <div
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-zinc-100 text-xs font-semibold text-zinc-600"
          aria-hidden="true"
        >
          {initials}
        </div>
        <div className="hidden text-left sm:block">
          <p className="text-xs text-zinc-500">{email}</p>
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

      {isOpen && (
        <>
          <button
            type="button"
            aria-label="Fermer le menu"
            className="fixed inset-0 z-40 cursor-default"
            onClick={() => setIsOpen(false)}
          />
          <div
            role="menu"
            className="absolute right-0 top-full z-50 mt-2 w-48 rounded-xl border border-zinc-200 bg-white p-1 shadow-lg"
          >
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setIsOpen(false);
                logout();
              }}
              className="w-full rounded-lg px-3 py-2 text-left text-sm text-zinc-700 transition-colors hover:bg-zinc-100"
            >
              Se déconnecter
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export function TopHeader() {
  const pathname = usePathname();
  const pageTitle = getPageTitle(pathname);
  const { isAuthenticated, email } = useAuth();

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
        {isAuthenticated && email ? <UserMenu email={email} /> : <LoginButton />}
      </div>
    </header>
  );
}

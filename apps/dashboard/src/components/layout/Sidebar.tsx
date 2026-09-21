"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { EnerVisionLogo } from "@/components/layout/EnerVisionLogo";
import { NAV_ITEMS, type NavIcon, type NavItem } from "@/config/navigation";

function NavIconSvg({ icon }: { icon: NavIcon }) {
  if (icon === "dashboard") {
    return (
      <svg
        className="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.75}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25"
        />
      </svg>
    );
  }

  if (icon === "sites") {
    return (
      <svg
        className="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.75}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21"
        />
      </svg>
    );
  }

  if (icon === "prediction") {
    return (
      <svg
        className="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.75}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M2.25 18L9 11.25l4.306 4.306a11.95 11.95 0 015.814-5.518l2.74-1.22m0 0l-5.94-2.281m5.94 2.28l-2.28 5.941"
        />
      </svg>
    );
  }

  return null;
}

function LogoutButton() {
  return (
    <button
      type="button"
      title="Se déconnecter"
      aria-label="Se déconnecter"
      className="flex h-11 w-11 items-center justify-center rounded-xl text-zinc-500 transition-colors hover:bg-zinc-100 hover:text-zinc-900"
      onClick={() => {
        // Auth non branchée — à connecter au flux de déconnexion JWT
      }}
    >
      <svg
        className="h-5 w-5"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={1.75}
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M15.75 9V5.25A2.25 2.25 0 0013.5 3h-6a2.25 2.25 0 00-2.25 2.25v13.5A2.25 2.25 0 007.5 21h6a2.25 2.25 0 002.25-2.25V15m3 0l3-3m0 0l-3-3m3 3H9"
        />
      </svg>
    </button>
  );
}

function SidebarNavItem({ item, isActive }: { item: NavItem; isActive: boolean }) {
  return (
    <Link
      href={item.href}
      title={item.label}
      aria-label={item.label}
      aria-current={isActive ? "page" : undefined}
      className={`flex h-11 w-11 items-center justify-center rounded-xl transition-colors ${
        isActive
          ? "bg-zinc-900 text-white shadow-sm"
          : "text-zinc-500 hover:bg-zinc-100 hover:text-zinc-900"
      }`}
    >
      <NavIconSvg icon={item.icon} />
    </Link>
  );
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside
      className="sticky top-0 flex h-screen w-[var(--sidebar-width)] shrink-0 flex-col items-center px-3 py-6"
      aria-label="Navigation principale"
    >
      <nav
        className="flex h-full w-full flex-col items-center rounded-2xl border border-zinc-200/80 bg-white py-5 shadow-sm"
        style={{ boxShadow: "var(--card-shadow)" }}
      >
        <div className="mb-8" aria-label="EnerVision">
          <EnerVisionLogo />
        </div>

        <ul className="flex flex-col items-center gap-2">
          {NAV_ITEMS.map((item) => {
            const isActive =
              item.href === "/"
                ? pathname === "/"
                : pathname.startsWith(item.href);

            return (
              <li key={item.href}>
                <SidebarNavItem item={item} isActive={isActive} />
              </li>
            );
          })}
        </ul>

        <div className="mt-auto pt-4">
          <LogoutButton />
        </div>
      </nav>
    </aside>
  );
}

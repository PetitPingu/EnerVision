export type NavIcon = "dashboard" | "prediction" | "sites" | "prediction";

export type NavItem = {
  label: string;
  href: string;
  icon: NavIcon;
  adminOnly?: boolean;
};

export const NAV_ITEMS: NavItem[] = [
  {
    label: "Dashboard",
    href: "/",
    icon: "dashboard",
  },
  {
    label: "Sites",
    href: "/sites",
    icon: "sites",
  },
  {
    label: "Prédictions & Recommandations",
    href: "/prediction",
    icon: "prediction",
  },
  {
    label: "Administration",
    href: "/admin",
    icon: "admin",
    adminOnly: true,
  },
];

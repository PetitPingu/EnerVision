export type NavIcon = "dashboard" | "sites" | "prediction";

export type NavItem = {
  label: string;
  href: string;
  icon: NavIcon;
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
];

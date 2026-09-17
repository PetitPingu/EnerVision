export type NavIcon = "dashboard" | "prediction";

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
    label: "Prévision",
    href: "/prediction",
    icon: "prediction",
  },
];

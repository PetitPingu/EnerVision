export type NavIcon = "dashboard";

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
];

export function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="shrink-0 border-t border-zinc-200/80 bg-zinc-50 px-6 py-4 text-center text-sm text-zinc-500 lg:px-10">
      <p>© {year} EnerVision. Tous droits réservés.</p>
    </footer>
  );
}

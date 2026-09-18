import { AuthGate } from "@/components/layout/AuthGate";
import { Footer } from "@/components/layout/Footer";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopHeader } from "@/components/layout/TopHeader";
import { AuthProvider } from "@/contexts/AuthContext";
import { SiteSelectionProvider } from "@/contexts/SiteSelectionContext";

type DashboardShellProps = {
  children: React.ReactNode;
};

export function DashboardShell({ children }: DashboardShellProps) {
  return (
    <AuthProvider>
      <SiteSelectionProvider>
        <div className="flex min-h-screen bg-zinc-50">
          <Sidebar />
          <div className="flex min-w-0 flex-1 flex-col">
            <TopHeader />
            <AuthGate>{children}</AuthGate>
            <Footer />
          </div>
        </div>
      </SiteSelectionProvider>
    </AuthProvider>
  );
}

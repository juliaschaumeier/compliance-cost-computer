"use client";

import { usePathname } from "next/navigation";

import AuthGate from "@/components/AuthGate";
import Header from "@/components/Header";
import TabBar from "@/components/TabBar";
import { AppProvider } from "@/contexts/AppContext";
import { AuthProvider } from "@/contexts/AuthContext";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isPublicLegalPage = pathname === "/impressum";

  if (isPublicLegalPage) {
    return <>{children}</>;
  }

  return (
    <AuthProvider>
      <AuthGate>
        <AppProvider>
          <div className="flex min-h-screen flex-col">
            <div className="sticky top-0 z-40">
              <Header />
              <TabBar />
            </div>
            <main className="flex-1">{children}</main>
          </div>
        </AppProvider>
      </AuthGate>
    </AuthProvider>
  );
}

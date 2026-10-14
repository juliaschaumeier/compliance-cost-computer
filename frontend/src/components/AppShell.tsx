"use client";

import { usePathname } from "next/navigation";

import AuthGate from "@/components/AuthGate";
import Header from "@/components/Header";
import TabBar from "@/components/TabBar";
import UploadPanel from "@/components/UploadPanel";
import { AppProvider, useApp } from "@/contexts/AppContext";
import { AuthProvider } from "@/contexts/AuthContext";

function WorkflowShell({ children }: { children: React.ReactNode }) {
  const { state } = useApp();
  const isPreparing = state.currentTab === 0;

  return (
    <div className="flex min-h-screen flex-col">
      <div className={`sticky top-0 z-40 ${isPreparing ? "flex max-h-dvh flex-col" : ""}`}>
        <div className="shrink-0">
          <Header />
          <TabBar />
        </div>
        {isPreparing && (
          // Keep preparation visible; stacked cards can scroll within the viewport.
          <div className="min-h-0 overflow-y-auto">
            <UploadPanel />
          </div>
        )}
      </div>
      <main className="flex-1">{children}</main>
    </div>
  );
}

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
          <WorkflowShell>{children}</WorkflowShell>
        </AppProvider>
      </AuthGate>
    </AuthProvider>
  );
}

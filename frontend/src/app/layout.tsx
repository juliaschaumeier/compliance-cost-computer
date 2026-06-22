import type { Metadata } from "next";

import "@fontsource/space-grotesk/300.css";
import "@fontsource/space-grotesk/400.css";
import "@fontsource/space-grotesk/500.css";
import "@fontsource/space-grotesk/600.css";
import "@fontsource/space-grotesk/700.css";
import "@fontsource/jetbrains-mono/400.css";
import "@fontsource/jetbrains-mono/500.css";
import "@fontsource/jetbrains-mono/700.css";
import "./globals.css";
import AuthGate from "@/components/AuthGate";
import Header from "@/components/Header";
import TabBar from "@/components/TabBar";
import { AppProvider } from "@/contexts/AppContext";
import { AuthProvider } from "@/contexts/AuthContext";

export const metadata: Metadata = {
  title: "CCC App",
  description: "Compliance-Cost Computer",
  icons: {
    icon: "/favicon.ico",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de">
      <body>
        <AuthProvider>
          <AuthGate>
            <AppProvider>
              <div className="min-h-screen flex flex-col">
                <div className="sticky top-0 z-40">
                  <Header />
                  <TabBar />
                </div>
                <main className="flex-1">
                  {children}
                </main>
              </div>
            </AppProvider>
          </AuthGate>
        </AuthProvider>
      </body>
    </html>
  );
}

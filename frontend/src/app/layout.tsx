import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";

import "./globals.css";
import Header from "@/components/Header";
import TabBar from "@/components/TabBar";
import { AppProvider } from "@/contexts/AppContext";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space",
});

const jetBrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jet",
});

export const metadata: Metadata = {
  title: "CCC App",
  description: "Compliance-Cost Computer",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="de" className={`${spaceGrotesk.variable} ${jetBrainsMono.variable}`}>
      <body>
        <AppProvider>
          <div className="min-h-screen flex flex-col">
            <Header />
            <TabBar />
            <main className="flex-1 px-4 sm:px-6 lg:px-10 py-6">
              {children}
            </main>
          </div>
        </AppProvider>
      </body>
    </html>
  );
}

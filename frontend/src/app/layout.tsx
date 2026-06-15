import type { Metadata } from "next";
import { JetBrains_Mono, Space_Grotesk } from "next/font/google";

import "./globals.css";
import Header from "@/components/Header";
import PaletteVariantLoader from "@/components/PaletteVariantLoader";
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
    <html lang="de" className={`${spaceGrotesk.variable} ${jetBrainsMono.variable}`}>
      <body>
        <PaletteVariantLoader />
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
      </body>
    </html>
  );
}

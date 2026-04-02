import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { TopNav } from "@/components/top-nav";
import { AuthProvider } from "@/components/AuthProvider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "SYAU AI — Creative Studio",
  description: "Self-hosted AI creative studio",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <AuthProvider>
          <div className="min-h-screen bg-background flex flex-col">
            <header className="border-b border-border px-6 py-3 flex items-center justify-between gap-6 bg-background/95 backdrop-blur">
              <div className="flex items-center gap-4">
                <span className="font-semibold text-lg tracking-tight">SYAU AI</span>
                <span className="hidden md:inline text-xs uppercase tracking-[0.24em] text-muted-foreground">
                  Creative Studio
                </span>
              </div>
              <TopNav />
            </header>
            <main className="flex-1">{children}</main>
          </div>
        </AuthProvider>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/ui/ThemeProvider";
import { Header } from "@/components/ui/Header";


const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: {
    default: "Tech Radar Express",
    template: "%s | Tech Radar Express",
  },
  description: "Plateforme de veille technologique intelligente avec IA et analyse conversationnelle",
  keywords: ["veille technologique", "intelligence artificielle", "tech radar", "analyse", "technologie"],
  authors: [{ name: "Tech Radar Express Team" }],
  creator: "Tech Radar Express",
  publisher: "Tech Radar Express",
  robots: {
    index: true,
    follow: true,
  },
  icons: {
    icon: "/favicon.ico",
  },
  viewport: {
    width: "device-width",
    initialScale: 1,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased min-h-screen 
                   bg-background text-foreground transition-colors duration-300`}
      >
        <ThemeProvider defaultTheme="system">
          <div className="flex min-h-screen flex-col">
            <Header />
            <main className="flex-1">
              {children}
            </main>
            <footer className="border-t border-gray-200 dark:border-gray-800 py-6 
                               bg-gray-50 dark:bg-gray-900/50">
              <div className="container mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex flex-col md:flex-row justify-between items-center gap-4">
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    © 2025 Tech Radar Express. Alimenté par MCP crawl4ai-rag + Local AI Stack.
                  </div>
                  <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400">
                    <span>🚀 FastAPI + Next.js</span>
                    <span>•</span>
                    <span>🤖 Ollama + MCP</span>
                    <span>•</span>
                    <span>📊 Supabase + Neo4j</span>
                  </div>
                </div>
              </div>
            </footer>
          </div>
        </ThemeProvider>
      </body>
    </html>
  );
}

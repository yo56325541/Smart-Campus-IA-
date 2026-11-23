import type { Metadata, Viewport } from "next";
import { Inter, Geist_Mono } from "next/font/google";
import { CampusProvider } from "@/components/providers/CampusProvider";
import "./globals.css";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
  weight: ["300", "400", "500", "600", "700", "800"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "SmartCampus AI",
    template: "%s | SmartCampus AI",
  },
  description:
    "Plateforme d'orientation universitaire intelligente — IIT & ISB. Découvrez nos formations, déposez votre candidature et suivez votre dossier en ligne.",
  keywords: ["université", "candidature", "formation", "IIT", "ISB", "orientation", "Tunisie"],
  authors: [{ name: "SmartCampus AI" }],
  robots: "index, follow",
  openGraph: {
    type: "website",
    locale: "fr_FR",
    siteName: "SmartCampus AI",
    title: "SmartCampus AI — Votre avenir commence ici",
    description: "Plateforme d'orientation universitaire intelligente pour IIT & ISB.",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#142A49",
};

interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html
      lang="fr"
      dir="ltr"
      className={`${inter.variable} ${geistMono.variable}`}
    >
      <body className="min-h-screen flex flex-col antialiased bg-bg text-text">
        <CampusProvider>{children}</CampusProvider>
      </body>
    </html>
  );
}

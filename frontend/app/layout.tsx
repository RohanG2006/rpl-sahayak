import type { Metadata, Viewport } from "next";
import { IBM_Plex_Sans, IBM_Plex_Mono, Noto_Sans_Devanagari } from "next/font/google";
import "./globals.css";
import Providers from "./providers";

const plex = IBM_Plex_Sans({ variable: "--font-plex", subsets: ["latin"], weight: ["400", "500", "600", "700"] });
const plexMono = IBM_Plex_Mono({ variable: "--font-plex-mono", subsets: ["latin"], weight: ["400", "500"] });
const deva = Noto_Sans_Devanagari({ variable: "--font-deva", subsets: ["devanagari"], weight: ["400", "500", "600", "700"] });

export const metadata: Metadata = {
  title: { default: "RPL-Sahayak AI", template: "%s · RPL-Sahayak AI" },
  description:
    "AI-Assisted Prior Learning Assessment & Assessor Support Platform — SIH26242 prototype. Final certification decisions remain with authorised human assessors.",
  applicationName: "RPL-Sahayak AI",
};

export const viewport: Viewport = {
  themeColor: "#16191d",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${plex.variable} ${plexMono.variable} ${deva.variable} h-full antialiased`}>
      <body className="min-h-full flex flex-col"><Providers>{children}</Providers></body>
    </html>
  );
}

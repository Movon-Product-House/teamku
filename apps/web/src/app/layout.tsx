import "./globals.css";
import type { Metadata } from "next";
import { Newsreader, Plus_Jakarta_Sans } from "next/font/google";
import type { ReactNode } from "react";
import { Providers } from "./providers";

const sans = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-jakarta" });
const display = Newsreader({ subsets: ["latin"], variable: "--font-newsreader" });

export const metadata: Metadata = {
  title: "Teamku",
  description: "Teamku — powered by movon digital house",
};

// Variabel font dipasang di <html>, tetapi body tetap memakai font legacy.
// Permukaan v2 memilih font lewat utility `font-sans` / `font-display`.
export default function Layout({ children }: { children: ReactNode }) {
  return (
    <html lang="id" className={`${sans.variable} ${display.variable}`}>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}

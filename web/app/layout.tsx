import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000"),
  title: "SimuMundial",
  description: "Armá, revelá y compartí tu Mundial 2026 simulado.",
  openGraph: {
    title: "SimuMundial",
    description: "Armá, revelá y compartí tu Mundial 2026 simulado.",
    images: ["/api/og"],
  },
  twitter: {
    card: "summary_large_image",
    title: "SimuMundial",
    description: "Armá, revelá y compartí tu Mundial 2026 simulado.",
    images: ["/api/og"],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es-AR">
      <body>{children}</body>
    </html>
  );
}

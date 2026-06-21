import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Terra.OS | Earthworks Management System",
  description: "Interactive simulation of the Terra.OS platform for construction companies.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pl">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}

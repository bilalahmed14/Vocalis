import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Vocalis",
  description: "Visual voice agent builder",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}

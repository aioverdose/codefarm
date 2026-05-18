import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Local Agent App Factory",
  description: "Deploy local autonomous agents that build sandboxed app scaffolds from prompts."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
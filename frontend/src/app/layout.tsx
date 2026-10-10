import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Recall — Course-Aware Adaptive Learning Platform",
  description: "Course-aware adaptive learning platform with deterministic authority, grounded AI remediation, and verified curriculum provenance.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-background text-foreground min-h-screen antialiased selection:bg-brand-yellow selection:text-ink">
        {children}
      </body>
    </html>
  );
}

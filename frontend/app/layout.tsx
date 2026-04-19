import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AutonomyX Agent Identity Plane",
  description: "Enterprise identity, policy, and lifecycle plane for AI agents"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

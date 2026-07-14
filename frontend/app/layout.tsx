import type { Metadata } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "EvidenceGraph",
    template: "%s | EvidenceGraph",
  },
  description:
    "A research intelligence workspace built around inspectable, source-linked evidence.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

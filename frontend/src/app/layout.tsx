import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VoiceActions AI — Speak Messy. Get Clarity.",
  description: "AI-powered voice & document analyzer. Extract action items, detect conflicts, flag ambiguity.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}

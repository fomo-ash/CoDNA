import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const inter = localFont({
  src: "./fonts/Inter-Latin.woff2",
  variable: "--font-inter",
  weight: "100 900",
  display: "swap",
});

const sourceSerif = localFont({
  src: "./fonts/SourceSerif4-Latin.woff2",
  variable: "--font-source-serif",
  weight: "200 900",
  display: "swap",
});

export const metadata: Metadata = {
  title: "CoDNA — Every codebase has a DNA. We help you decode it.",
  description: "AI-powered software intelligence platform that enables developers to understand complex codebases, map dependencies, and query structures.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${sourceSerif.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}

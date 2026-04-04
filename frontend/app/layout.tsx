import type { Metadata } from "next";
import "./globals.css";
import AuthLayout from "@/components/AuthLayout";

export const metadata: Metadata = {
  title: "AdNova India — AI Ad Optimizer",
  description: "Premium AI-powered Meta Ads optimizer built for Indian D2C founders. Analyze business metrics, optimize creatives, and target the right audience.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <AuthLayout>{children}</AuthLayout>
      </body>
    </html>
  );
}

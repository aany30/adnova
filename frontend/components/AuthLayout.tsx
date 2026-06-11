"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import AuthGuard from "@/components/AuthGuard";
import { getUser } from "@/lib/auth";

const AUTH_ROUTES = ["/login", "/signup"];

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isAuthPage = AUTH_ROUTES.includes(pathname);
  const authDisabled = process.env.NEXT_PUBLIC_DISABLE_AUTH === "true";
  const user = getUser();
  const adminEmails = (process.env.NEXT_PUBLIC_ADMIN_EMAILS || "")
    .split(",")
    .map((email) => email.trim().toLowerCase())
    .filter(Boolean);
  const canSeeAdmin = authDisabled || (user?.email && adminEmails.includes(user.email.toLowerCase()));
  const showAdminShortcut = canSeeAdmin && pathname !== "/admin";

  const adminShortcut = showAdminShortcut ? (
    <Link href="/admin" className="admin-corner-shortcut" aria-label="Open admin panel">
      <span className="admin-corner-icon">
        <svg width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path d="M12 2l7 4v6c0 5-3 8-7 10-4-2-7-5-7-10V6l7-4z"/>
          <path d="M9 12l2 2 4-5"/>
        </svg>
      </span>
      <span>Admin</span>
    </Link>
  ) : null;

  if (isAuthPage) {
    // Auth pages: full-screen, no sidebar
    return <>{children}</>;
  }

  if (authDisabled) {
    return (
      <div style={{ display: "flex", minHeight: "100vh" }}>
        <Sidebar />
        <main style={{ flex: 1, overflowY: "auto" }}>
          {adminShortcut}
          {children}
        </main>
      </div>
    );
  }

  // App pages: protected, with sidebar
  return (
    <AuthGuard>
      <div style={{ display: "flex", minHeight: "100vh" }}>
        <Sidebar />
        <main style={{ flex: 1, overflowY: "auto" }}>
          {adminShortcut}
          {children}
        </main>
      </div>
    </AuthGuard>
  );
}

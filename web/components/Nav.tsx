"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "./ThemeToggle";

const LINKS = [
  { href: "/", label: "Console", exact: true },
  { href: "/ledger", label: "Ledger", exact: false },
  { href: "/runs", label: "Runs", exact: false },
  { href: "/profile", label: "Profile", exact: false },
];

export function Nav() {
  const path = usePathname();
  const isActive = (href: string, exact: boolean) => (exact ? path === href : path.startsWith(href));
  return (
    <nav className="nav" aria-label="Primary">
      <Link href="/" className="brand">
        Allocation Console
      </Link>
      {LINKS.map((l) => (
        <Link key={l.href} href={l.href} className={isActive(l.href, l.exact) ? "active" : ""}>
          {l.label}
        </Link>
      ))}
      <ThemeToggle />
    </nav>
  );
}

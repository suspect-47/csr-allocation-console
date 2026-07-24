import type { ReactNode } from "react";
import { Nav } from "@/components/Nav";

// Operator console chrome (CSR allocation console). The marketplace at /market
// renders its own chrome and does not use this layout.
export default function SiteLayout({ children }: { children: ReactNode }) {
  return (
    <div className="app">
      <Nav />
      <main className="container">{children}</main>
    </div>
  );
}

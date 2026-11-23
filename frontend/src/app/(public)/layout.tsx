import React from "react";
import { Suspense } from "react";
import { Navbar } from "@/components/layout/Navbar";
import { Footer } from "@/components/layout/Footer";

/**
 * Layout Public — Navbar + contenu + Footer
 * Utilisé par la landing page, le catalogue, les pages statiques.
 * Phase 2 : user viendra de AuthContext.
 */
export default function PublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Suspense
        fallback={
          <div
            aria-hidden="true"
            className="h-16 border-b border-border bg-white"
          />
        }
      >
        <Navbar />
      </Suspense>
      <main className="flex-1">{children}</main>
      <Footer />
    </>
  );
}

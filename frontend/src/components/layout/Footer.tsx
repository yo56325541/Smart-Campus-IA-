import React from "react";
import Link from "next/link";
import { GraduationCap } from "lucide-react";

// ─── Données statiques ────────────────────────────────────────────────────────

const footerLinks = {
  formations: {
    title: "Formations",
    links: [
      { label: "Toutes les formations", href: "/programmes" },
      { label: "IIT — Institut de Technologie", href: "/programmes?institution=IIT" },
      { label: "ISB — Institut de Business", href: "/programmes?institution=ISB" },
      { label: "Licences", href: "/programmes?level=licence" },
      { label: "Prépa", href: "/programmes?level=prepa" },
    ],
  },
  orientation: {
    title: "Orientation",
    links: [
      { label: "Parcourir les formations", href: "/programmes" },
    ],
  },
  institutions: {
    title: "Institutions",
    links: [
      { label: "IIT", href: "/programmes?institution=IIT" },
      { label: "ISB", href: "/programmes?institution=ISB" },
    ],
  },
};

// ─── Composant principal ──────────────────────────────────────────────────────

export function Footer() {
  return (
    <footer className="bg-navy-800 text-white">

      {/* Corps principal */}
      <div className="container-page py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-10">

          {/* Colonne Brand */}
          <div className="lg:col-span-1">
            <Link href="/" className="flex items-center gap-2.5 group mb-5">
              <span className="flex items-center justify-center w-10 h-10 rounded-xl bg-turquoise-500 text-white shadow-sm">
                <GraduationCap className="w-5 h-5" />
              </span>
              <span className="flex flex-col leading-tight">
                <span className="text-base font-bold tracking-tight">SmartCampus</span>
                <span className="text-[10px] font-semibold text-turquoise-400 tracking-widest uppercase -mt-0.5">AI</span>
              </span>
            </Link>

            <p className="text-sm text-navy-200 leading-relaxed mb-6">
              Votre plateforme d’orientation universitaire. Découvrez les
              formations de l’IIT et de l’ISB, ainsi que les informations
              d’admission et de tarifs disponibles.
            </p>
          </div>

          {/* Colonnes Navigation */}
          {Object.entries(footerLinks).map(([key, section]) => (
            <div key={key}>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4">
                {section.title}
              </h3>
              <ul className="flex flex-col gap-2.5">
                {section.links.map(link => (
                  <li key={link.href}>
                    <Link
                      href={link.href}
                      className="text-sm text-navy-300 hover:text-turquoise-400 transition-colors duration-150 flex items-center gap-1 group"
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </div>

      {/* Barre de copyright */}
      <div className="border-t border-navy-700">
        <div className="container-page py-5 flex flex-col sm:flex-row items-center justify-between gap-3">
          <p className="text-sm text-navy-400 text-center sm:text-left">
            SmartCampus AI. Tous droits réservés.
          </p>
        </div>
      </div>
    </footer>
  );
}

export function CandidatePageHeader({
  title,
  description,
  eyebrow = "Espace candidat",
}: {
  title: string;
  description: string;
  eyebrow?: string;
}) {
  return (
    <header className="mb-8">
      <p className="mb-2 text-xs font-bold uppercase tracking-[0.16em] text-turquoise-700">
        {eyebrow}
      </p>
      <h1 className="text-2xl font-bold tracking-tight text-navy-800 sm:text-3xl">
        {title}
      </h1>
      <p className="mt-2 max-w-3xl text-sm leading-relaxed text-text-muted sm:text-base">
        {description}
      </p>
    </header>
  );
}

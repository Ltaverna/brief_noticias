export function Footer({ generatedAt }: { generatedAt?: string | null }) {
  return (
    <footer className="border-t border-stone-200 px-6 py-6 text-xs text-stone-500 dark:border-stone-800 dark:text-stone-400">
      <div className="mx-auto max-w-5xl">
        {generatedAt && <p>Briefing generado: {new Date(generatedAt).toLocaleString("es-AR")}</p>}
        <p className="mt-1">Comparador de coberturas · Análisis con GPT-4o</p>
      </div>
    </footer>
  );
}

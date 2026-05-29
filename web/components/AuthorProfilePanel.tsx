"use client";
import { useEffect, useState } from "react";
import {
  getAuthorProfile, regenerateAuthorProfile, type AuthorProfile,
} from "@/lib/authors";

const MIN_N = 3;

export function AuthorProfilePanel({ slug, nSample }: { slug: string; nSample: number }) {
  const [profile, setProfile] = useState<AuthorProfile | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => { getAuthorProfile(slug).then(setProfile); }, [slug]);

  const insufficient = nSample < MIN_N;

  async function generate() {
    setLoading(true); setErr(null);
    try {
      const r = await regenerateAuthorProfile(slug);
      setProfile(r);
    } catch (e) {
      setErr(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <p className="text-sm text-slate-500">
          {profile
            ? `Última generación: ${new Date(profile.generated_at).toLocaleDateString()} · muestra ${profile.n_sample}`
            : "Sin perfil generado aún"}
        </p>
        <button
          onClick={generate}
          disabled={insufficient || loading}
          title={insufficient ? `Se necesitan al menos ${MIN_N} análisis` : ""}
          className="px-3 py-1.5 text-sm rounded bg-blue-600 text-white hover:bg-blue-700 disabled:bg-slate-300 disabled:cursor-not-allowed"
        >
          {loading ? "Generando…" : profile ? "Regenerar" : "Generar perfil"}
        </button>
      </div>

      {err && <p className="text-sm text-red-600">{err}</p>}

      {profile && (
        <div className="space-y-3 text-sm">
          <Field label="Tono característico" value={profile.profile.tono_caracteristico} />
          <ListField label="Framings recurrentes" items={profile.profile.framings_recurrentes} />
          <ListField label="Fuentes citadas" items={profile.profile.fuentes_citadas_frecuentes} />
          <ListField label="Entidades dominantes" items={profile.profile.entidades_dominantes} />
          <ListField label="Temas evitados" items={profile.profile.temas_evitados} />
        </div>
      )}
    </div>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  if (!value) return null;
  return (
    <div>
      <div className="text-xs text-slate-500 uppercase mb-1">{label}</div>
      <p>{value}</p>
    </div>
  );
}

function ListField({ label, items }: { label: string; items: string[] }) {
  if (!items?.length) return null;
  return (
    <div>
      <div className="text-xs text-slate-500 uppercase mb-1">{label}</div>
      <ul className="list-disc list-inside space-y-1">
        {items.map((s, i) => <li key={i}>{s}</li>)}
      </ul>
    </div>
  );
}

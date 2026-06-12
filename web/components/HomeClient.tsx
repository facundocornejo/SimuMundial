"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SAVED_KEY } from "@/lib/storage-keys";

type SavedProde = {
  id: string;
  player: string;
  code: string;
  champion?: string | null;
  updatedAt: string;
};

function readSaved(): SavedProde[] {
  try {
    return JSON.parse(localStorage.getItem(SAVED_KEY) ?? "[]") as SavedProde[];
  } catch {
    return [];
  }
}

export function HomeClient() {
  const [saved, setSaved] = useState<SavedProde[]>([]);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    setSaved(readSaved());
  }, []);

  function clearSaved() {
    localStorage.removeItem(SAVED_KEY);
    setSaved([]);
    setConfirmDelete(false);
  }

  return (
    <main className="home-shell">
      <section className="home-hero">
        <div className="home-copy">
          <p className="eyebrow">Prode Mundial 2026</p>
          <h1>Armá tu Mundial antes de que empiece el ruido.</h1>
          <p>
            Cargá los 72 partidos de grupos, completá lo que falte con el modelo
            y compartí un link que después revela tu camino hasta la copa.
          </p>
          <div className="hero-actions">
            <Link className="button button--primary" href="/prode">
              Armá tu prode
            </Link>
            {saved[0] ? (
              <Link className="button button--ghost" href={`/mundial?p=${saved[0].code}`}>
                Ver último
              </Link>
            ) : null}
          </div>
        </div>

        <aside className="saved-panel" aria-label="Tus prodes guardados">
          <div className="panel-heading">
            <p className="eyebrow">Tus prodes</p>
            <span>{saved.length}</span>
          </div>
          {saved.length === 0 ? (
            <p className="empty-copy">
              Todavía no guardaste ninguno. Cuando confirmes un prode, aparece
              acá con su link para seguirlo.
            </p>
          ) : (
            <ul className="saved-list">
              {saved.map((item) => (
                <li key={item.id}>
                  <Link href={`/mundial?p=${item.code}`}>
                    <strong>{item.player}</strong>
                    <span>{item.champion ? `Campeón: ${item.champion}` : "Listo para revelar"}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
          {saved.length > 0 ? (
            !confirmDelete ? (
              <button className="button button--ghost clear-saved" type="button" onClick={() => setConfirmDelete(true)}>
                Borrar prodes guardados
              </button>
            ) : (
              <div className="inline-confirm inline-confirm--saved">
                <span>Esto borra sólo los prodes guardados en este navegador.</span>
                <button type="button" onClick={clearSaved}>Borrar</button>
                <button type="button" onClick={() => setConfirmDelete(false)}>Cancelar</button>
              </div>
            )
          ) : null}
        </aside>
      </section>
    </main>
  );
}

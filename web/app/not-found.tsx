import Link from "next/link";

export default function NotFound() {
  return (
    <main className="home-shell not-found-shell">
      <section className="home-hero">
        <div className="home-copy">
          <p className="eyebrow">Prode Mundial 2026</p>
          <h1>No encontramos esa pantalla.</h1>
          <p>Volvé al inicio o cargá un prode nuevo para generar un link válido.</p>
          <div className="hero-actions">
            <Link className="button button--primary" href="/">
              Ir al inicio
            </Link>
            <Link className="button button--ghost" href="/prode?new=1">
              Armar prode
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { ChangeEvent, KeyboardEvent, TouchEvent, useEffect, useMemo, useState } from "react";
import { GROUP_CODES, ES } from "@/lib/teams";
import { encodeProde } from "@/lib/prode-codec";
import { clampGoal, normalizeImportedProde, validateProde } from "@/lib/prode-validation";
import { groupMatches, orderedMatchIds } from "@/lib/match-order";
import { scoreProde } from "@/lib/scoring";
import { DRAFT_KEY, SAVED_KEY } from "@/lib/storage-keys";
import type { Match, Prode, Score } from "@/lib/types";

type Prediction = {
  score_pred?: Score;
};

type SavedProde = {
  id: string;
  player: string;
  code: string;
  champion: string | null;
  updatedAt: string;
};

const QUICK_SCORES: Score[] = [
  [0, 0],
  [1, 0],
  [2, 0],
  [2, 1],
  [1, 1],
  [3, 0],
  [3, 1],
];

type Draft = {
  player: string;
  results: Record<string, Score>;
  modelFilled: string[];
  index: number;
  mode: "card" | "sheet";
};

function scoreLabel(score?: Score) {
  return score ? `${score[0]}-${score[1]}` : "Sin cargar";
}

function readSaved(): SavedProde[] {
  try {
    return JSON.parse(localStorage.getItem(SAVED_KEY) ?? "[]") as SavedProde[];
  } catch {
    return [];
  }
}

function writeSaved(item: SavedProde) {
  const next = [item, ...readSaved().filter((saved) => saved.id !== item.id)].slice(0, 12);
  localStorage.setItem(SAVED_KEY, JSON.stringify(next));
}

export function ProdeBuilder({
  matches,
  predictions,
  modelPicks,
  initialProde,
  forceNew = false,
}: {
  matches: Match[];
  predictions: Record<string, Prediction>;
  modelPicks: Record<string, Score>;
  initialProde?: Prode | null;
  forceNew?: boolean;
}) {
  const router = useRouter();
  const matchIds = useMemo(() => orderedMatchIds(matches), [matches]);
  const grouped = useMemo(() => groupMatches(matches), [matches]);
  const [draft, setDraft] = useState<Draft>({
    player: "",
    results: {},
    modelFilled: [],
    index: 0,
    mode: "card",
  });
  const [initialized, setInitialized] = useState(false);
  const [importMessage, setImportMessage] = useState("");
  const [touchStart, setTouchStart] = useState<number | null>(null);
  const [pendingClear, setPendingClear] = useState(false);

  const current = matches[Math.min(draft.index, matches.length - 1)];
  const validation = useMemo(
    () => validateProde({ player: draft.player, results: draft.results }, matchIds),
    [draft.player, draft.results, matchIds],
  );
  const loadedCount = validation.imported;
  const resultsComplete = validation.missing.length === 0 && validation.invalid.length === 0 && validation.unknown.length === 0;
  const complete = validation.valid;
  const scoreSummary = useMemo(
    () => scoreProde({ player: draft.player || "draft", results: draft.results }, matches),
    [draft.player, draft.results, matches],
  );
  const modelFilledCount = draft.modelFilled.filter((matchId) => draft.results[matchId]).length;
  const currentModelScore = current
    ? predictions[current.match_id]?.score_pred ?? modelPicks[current.match_id]
    : null;
  const currentWasModelFilled = current ? draft.modelFilled.includes(current.match_id) : false;

  useEffect(() => {
    let nextDraft: Draft = {
      player: "",
      results: {},
      modelFilled: [],
      index: 0,
      mode: "card",
    };

    try {
      if (forceNew) {
        localStorage.removeItem(DRAFT_KEY);
        localStorage.removeItem("prode-mundial-2026:worldRevealState");
        setImportMessage("Carga nueva lista.");
      } else if (initialProde) {
        const normalized = normalizeImportedProde(initialProde, matchIds);
        nextDraft = {
          player: normalized.prode.player,
          results: normalized.prode.results,
          modelFilled: [],
          index: 0,
          mode: "card",
        };
        setImportMessage(`Prode cargado para editar: ${normalized.report.imported}/72 partidos.`);
      } else {
        const raw = localStorage.getItem(DRAFT_KEY);
        if (!raw) {
          setInitialized(true);
          return;
        }
        const saved = JSON.parse(raw) as Draft;
        const normalized = normalizeImportedProde(saved, matchIds);
        const known = new Set(matchIds);
        setDraft({
          player: normalized.prode.player,
          results: normalized.prode.results,
          modelFilled: Array.isArray(saved.modelFilled)
            ? saved.modelFilled.filter((matchId) => known.has(matchId))
            : [],
          index: Math.min(saved.index ?? 0, matches.length - 1),
          mode: saved.mode === "sheet" ? "sheet" : "card",
        });
        setInitialized(true);
        return;
      }
    } catch {
      localStorage.removeItem(DRAFT_KEY);
    }

    setDraft(nextDraft);
    setInitialized(true);
  }, [forceNew, initialProde, matchIds, matches.length]);

  useEffect(() => {
    if (!initialized) return;
    localStorage.setItem(DRAFT_KEY, JSON.stringify(draft));
  }, [draft, initialized]);

  function setScore(matchId: string, score: Score) {
    const normalized: Score = [clampGoal(score[0]), clampGoal(score[1])];
    setDraft((currentDraft) => ({
      ...currentDraft,
      results: { ...currentDraft.results, [matchId]: normalized },
      modelFilled: currentDraft.modelFilled.filter((filledId) => filledId !== matchId),
    }));
  }

  function move(delta: number) {
    setDraft((currentDraft) => ({
      ...currentDraft,
      index: Math.max(0, Math.min(matches.length - 1, currentDraft.index + delta)),
    }));
  }

  function nextEmpty() {
    const nextIndex = matches.findIndex((match) => !draft.results[match.match_id]);
    setDraft((currentDraft) => ({
      ...currentDraft,
      index: nextIndex === -1 ? matches.length - 1 : nextIndex,
      mode: "card",
    }));
  }

  function fillWithModel() {
    const nextResults = { ...draft.results };
    const modelFilled = new Set(draft.modelFilled);
    for (const match of matches) {
      if (nextResults[match.match_id]) continue;
      const modelScore = predictions[match.match_id]?.score_pred ?? modelPicks[match.match_id];
      if (modelScore) {
        nextResults[match.match_id] = modelScore;
        modelFilled.add(match.match_id);
      }
    }
    setDraft((currentDraft) => ({
      ...currentDraft,
      results: nextResults,
      modelFilled: [...modelFilled],
    }));
    setImportMessage("Completé los faltantes con el modelo.");
  }

  function confirmClearDraft() {
    const emptyDraft: Draft = {
      player: "",
      results: {},
      modelFilled: [],
      index: 0,
      mode: "card",
    };
    localStorage.removeItem(DRAFT_KEY);
    localStorage.removeItem("prode-mundial-2026:worldRevealState");
    setDraft(emptyDraft);
    setImportMessage("Carga limpiada.");
    setPendingClear(false);
  }

  async function importJson(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.size > 128 * 1024) {
      setImportMessage("Ese JSON es demasiado grande para un prode.");
      event.target.value = "";
      return;
    }
    try {
      const data = JSON.parse(await file.text()) as Prode;
      const normalized = normalizeImportedProde(data, matchIds);
      setDraft((currentDraft) => ({
        ...currentDraft,
        player: normalized.prode.player || currentDraft.player,
        results: normalized.prode.results,
        modelFilled: [],
        index: 0,
        mode: "card",
      }));
      const { report } = normalized;
      setImportMessage([
        `Importado: ${report.imported}/72 partidos.`,
        report.missing.length ? `Faltan ${report.missing.length}.` : "",
        report.unknown.length ? `Descarté ${report.unknown.length} ids desconocidos.` : "",
        report.invalid.length ? `Descarté ${report.invalid.length} resultados inválidos.` : "",
      ].filter(Boolean).join(" "));
    } catch {
      setImportMessage("No pude leer ese JSON.");
    } finally {
      event.target.value = "";
    }
  }

  function confirm() {
    const currentValidation = validateProde({ player: draft.player, results: draft.results }, matchIds);
    if (!currentValidation.valid) {
      setImportMessage(currentValidation.errors.join(" "));
      return;
    }
    const prode: Prode = { player: currentValidation.player, results: draft.results };
    const code = encodeProde(prode, matchIds);
    writeSaved({
      id: `${prode.player}-${Date.now()}`,
      player: prode.player,
      code,
      champion: null,
      updatedAt: new Date().toISOString(),
    });
    localStorage.removeItem(DRAFT_KEY);
    localStorage.removeItem("prode-mundial-2026:worldRevealState");
    router.push(`/mundial?p=${code}`);
  }

  function onCardKey(event: KeyboardEvent<HTMLElement>) {
    if (event.key === "Enter") move(1);
  }

  function onTouchEnd(event: TouchEvent<HTMLElement>) {
    if (touchStart === null) return;
    const delta = event.changedTouches[0].clientX - touchStart;
    if (delta < -48) move(1);
    if (delta > 48) move(-1);
    setTouchStart(null);
  }

  return (
    <main className="prode-shell">
      <header className="prode-header">
        <div>
          <p className="eyebrow">Carga del prode</p>
          <h1>Partido {Math.min(draft.index + 1, matches.length)}/72</h1>
        </div>
        <div className="progress-meter" aria-label={`${loadedCount} de ${matchIds.length} partidos cargados`}>
          <span style={{ width: `${(loadedCount / matchIds.length) * 100}%` }} />
        </div>
      </header>

      <section className="builder-layout">
        <aside className="builder-tools">
          <label className="field">
            <span>Nombre</span>
            <input
              value={draft.player}
              onChange={(event) => setDraft((currentDraft) => ({ ...currentDraft, player: event.target.value }))}
              placeholder="facu"
            />
          </label>

          <div className="segmented" aria-label="Modo de carga">
            <button
              type="button"
              className={draft.mode === "card" ? "is-active" : ""}
              onClick={() => setDraft((currentDraft) => ({ ...currentDraft, mode: "card" }))}
            >
              Carta
            </button>
            <button
              type="button"
              className={draft.mode === "sheet" ? "is-active" : ""}
              onClick={() => setDraft((currentDraft) => ({ ...currentDraft, mode: "sheet" }))}
            >
              Planilla
            </button>
          </div>

          <div className="source-summary" aria-label="Resumen de carga">
            <div>
              <span>Cargados</span>
              <strong>{loadedCount}/72</strong>
            </div>
            <div>
              <span>Faltantes</span>
              <strong>{validation.missing.length}</strong>
            </div>
            <div>
              <span>Reales acertados</span>
              <strong>{scoreSummary.exact} exactos · {scoreSummary.outcome} 1X2</strong>
            </div>
            <div>
              <span>Completados por modelo</span>
              <strong>{modelFilledCount}</strong>
            </div>
          </div>

          <button className="button button--secondary" type="button" onClick={fillWithModel}>
            Completar con modelo
          </button>
          <button className="button button--ghost" type="button" onClick={nextEmpty}>
            Ir al próximo vacío
          </button>
          {!pendingClear ? (
            <button className="button button--ghost" type="button" onClick={() => setPendingClear(true)}>
              Limpiar carga
            </button>
          ) : (
            <div className="inline-confirm">
              <span>Esto borra el draft local.</span>
              <button type="button" onClick={confirmClearDraft}>Borrar</button>
              <button type="button" onClick={() => setPendingClear(false)}>Cancelar</button>
            </div>
          )}

          <label className="file-button">
            Importar prode JSON
            <input accept="application/json" type="file" onChange={importJson} />
          </label>
          {importMessage ? <p className="import-message">{importMessage}</p> : null}

          <div className="completion-card">
            <strong>{loadedCount}/72</strong>
            <span>{resultsComplete ? "Todos los partidos tienen pronóstico" : "partidos cargados"}</span>
            {resultsComplete ? (
              <small>
                {validation.player || "Sin nombre"} · {scoreSummary.exact} exactos · {scoreSummary.outcome} 1X2 contra resultados reales jugados.
              </small>
            ) : (
              <small>Faltan {validation.missing.length} partidos antes de revelar.</small>
            )}
            <button className="button button--primary" type="button" disabled={!complete || !draft.player.trim()} onClick={confirm}>
              Confirmar y revelar
            </button>
          </div>
        </aside>

        {draft.mode === "card" && current ? (
          <section
            className="match-card"
            tabIndex={0}
            onKeyDown={onCardKey}
            onTouchStart={(event) => setTouchStart(event.touches[0].clientX)}
            onTouchEnd={onTouchEnd}
          >
            <div className="match-meta">
              <span className={`group-chip group-${current.group}`}>Grupo {current.group}</span>
              <span className="source-badge">Tu pronóstico</span>
              {current.status === "played" && current.score ? (
                <span className="real-badge">Resultado real: {scoreLabel(current.score)}</span>
              ) : null}
              {currentWasModelFilled ? (
                <span className="model-badge">Completado por modelo</span>
              ) : null}
            </div>

            <div className="teams-line">
              <strong>{current.home_es ?? ES[current.home] ?? current.home}</strong>
              <span>{scoreLabel(draft.results[current.match_id])}</span>
              <strong>{current.away_es ?? ES[current.away] ?? current.away}</strong>
            </div>

            <div className="result-context">
              <span>Tu pronóstico: {scoreLabel(draft.results[current.match_id])}</span>
              {current.score ? <span>Real: {scoreLabel(current.score)}</span> : <span>Real: pendiente</span>}
              {currentModelScore ? <span>Modelo: {scoreLabel(currentModelScore)}</span> : null}
            </div>

            <div className="quick-grid">
              {QUICK_SCORES.map((score) => (
                <button
                  key={`${score[0]}-${score[1]}`}
                  type="button"
                  className={scoreLabel(draft.results[current.match_id]) === scoreLabel(score) ? "is-active" : ""}
                  onClick={() => {
                    setScore(current.match_id, score);
                    move(1);
                  }}
                >
                  {scoreLabel(score)}
                </button>
              ))}
            </div>

            <div className="manual-score">
              <button type="button" onClick={() => setScore(current.match_id, [Math.max(0, (draft.results[current.match_id]?.[0] ?? 0) - 1), draft.results[current.match_id]?.[1] ?? 0])}>
                -
              </button>
              <span>{current.home_es ?? ES[current.home] ?? current.home}</span>
              <button type="button" onClick={() => setScore(current.match_id, [clampGoal((draft.results[current.match_id]?.[0] ?? 0) + 1), draft.results[current.match_id]?.[1] ?? 0])}>
                +
              </button>
              <button type="button" onClick={() => setScore(current.match_id, [draft.results[current.match_id]?.[0] ?? 0, Math.max(0, (draft.results[current.match_id]?.[1] ?? 0) - 1)])}>
                -
              </button>
              <span>{current.away_es ?? ES[current.away] ?? current.away}</span>
              <button type="button" onClick={() => setScore(current.match_id, [draft.results[current.match_id]?.[0] ?? 0, clampGoal((draft.results[current.match_id]?.[1] ?? 0) + 1)])}>
                +
              </button>
            </div>

            <div className="card-nav">
              <button className="button button--ghost" type="button" onClick={() => move(-1)} disabled={draft.index === 0}>
                Anterior
              </button>
              <button className="button button--primary" type="button" onClick={() => move(1)} disabled={draft.index === matches.length - 1}>
                Siguiente
              </button>
            </div>
          </section>
        ) : (
          <section className="sheet-view">
            {GROUP_CODES.map((group) => (
              <div className="group-block" key={group}>
                <h2>Grupo {group}</h2>
                <div className="sheet-list">
                  {(grouped[group] ?? []).map((match) => (
                    <div className="sheet-row" key={match.match_id}>
                      <span>{match.home_es ?? ES[match.home] ?? match.home}</span>
                      <input
                        aria-label={`Goles de ${match.home_es ?? match.home}`}
                        inputMode="numeric"
                        min={0}
                        type="number"
                        value={draft.results[match.match_id]?.[0] ?? ""}
                        max={9}
                        onChange={(event) => setScore(match.match_id, [clampGoal(event.target.value), draft.results[match.match_id]?.[1] ?? 0])}
                      />
                      <input
                        aria-label={`Goles de ${match.away_es ?? match.away}`}
                        inputMode="numeric"
                        min={0}
                        type="number"
                        value={draft.results[match.match_id]?.[1] ?? ""}
                        max={9}
                        onChange={(event) => setScore(match.match_id, [draft.results[match.match_id]?.[0] ?? 0, clampGoal(event.target.value)])}
                      />
                      <span>{match.away_es ?? ES[match.away] ?? match.away}</span>
                      <small>
                        {draft.modelFilled.includes(match.match_id) ? "Modelo" : "Pronóstico"}
                        {match.score ? ` · Real ${scoreLabel(match.score)}` : ""}
                      </small>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </section>
        )}
      </section>
    </main>
  );
}

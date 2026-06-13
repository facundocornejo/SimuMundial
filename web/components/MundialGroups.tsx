"use client";

import { AnimatePresence, motion } from "framer-motion";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { groupMatches } from "@/lib/match-order";
import type { KnockoutDraw } from "@/lib/draw";
import type { TeamStats } from "@/lib/standings";
import { DRAFT_KEY } from "@/lib/storage-keys";
import { ES, GROUP_CODES, type GroupCode } from "@/lib/teams";
import { PhaseAtmosphere } from "@/components/VisualBackdrop";
import { KnockoutBracket, roundNames, type RoundKey } from "@/components/KnockoutBracket";
import type { Match, Prode, Score } from "@/lib/types";

type Screen =
  | { kind: "group"; group: GroupCode; label: string; phase: "Grupos" }
  | { kind: "thirds"; label: string; phase: "Grupos" }
  | { kind: "round"; round: RoundKey; label: string; phase: string };

const phaseLabels = ["Grupos", "16avos", "8vos", "4tos", "Semis", "Final"];

const screenVariants = {
  initial: { opacity: 0, y: 26, scale: 0.985 },
  enter: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -18, scale: 0.99 },
};

function useReducedMotionPreference() {
  const [reduced, setReduced] = useState(false);

  useEffect(() => {
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduced(query.matches);
    const listener = () => setReduced(query.matches);
    query.addEventListener("change", listener);
    return () => query.removeEventListener("change", listener);
  }, []);

  return reduced;
}

function teamName(team: string) {
  return ES[team] ?? team;
}

function scoreText(score?: Score) {
  return score ? `${score[0]}-${score[1]}` : "--";
}

function phaseIndex(screen: Screen) {
  return Math.max(0, phaseLabels.indexOf(screen.phase));
}

function buildScreens(): Screen[] {
  return [
    ...GROUP_CODES.map((group) => ({
      kind: "group" as const,
      group,
      label: `Grupo ${group}`,
      phase: "Grupos" as const,
    })),
    { kind: "thirds" as const, label: "Mejores terceros", phase: "Grupos" as const },
    ...(["r32", "r16", "qf", "sf", "final"] as RoundKey[]).map((round) => ({
      kind: "round" as const,
      round,
      label: roundNames[round].label,
      phase: roundNames[round].phase,
    })),
  ];
}

function GroupScreen({
  group,
  matches,
  prode,
  ranked,
  table,
  thirds,
  reducedMotion,
}: {
  group: GroupCode;
  matches: Match[];
  prode: Prode;
  ranked: Record<string, string[]>;
  table: Record<string, TeamStats>;
  thirds: string[];
  reducedMotion: boolean;
}) {
  const teams = ranked[group] ?? [];

  return (
    <div className="phase-page phase-page--group">
      <div className="phase-copy">
        <span className={`group-chip group-${group}`}>Grupo {group}</span>
        <h2>Tu Grupo {group}</h2>
        <p>
          Tabla según tu pronóstico. Si ya existe resultado real, aparece como
          referencia secundaria y no reemplaza tu carga.
        </p>
      </div>

      <div className="group-arena">
        <div className="match-ledger" aria-label={`Partidos del grupo ${group}`}>
          {matches.map((match, index) => (
            <motion.div
              className="ledger-row"
              key={match.match_id}
              initial={reducedMotion ? false : { opacity: 0, x: -18 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: reducedMotion ? 0 : index * 0.055, duration: 0.32 }}
            >
              <span>{teamName(match.home)}</span>
              <strong>{scoreText(prode.results[match.match_id])}</strong>
              <span>{teamName(match.away)}</span>
              <small>
                Pronóstico principal
                {match.status === "played" && match.score ? ` · Resultado real: ${scoreText(match.score)}` : ""}
              </small>
            </motion.div>
          ))}
        </div>

        <div className="table-panel">
          <div className="table-caption">Tabla según tu pronóstico</div>
          <motion.ol className="table-stack" layout aria-label={`Tabla del grupo ${group}`}>
            {teams.map((team, index) => {
              const stats = table[team];
              const className = index < 2 ? "is-direct" : thirds.includes(team) ? "is-third" : "";
              return (
                <motion.li className={className} key={team} layout>
                  <span>{index + 1}</span>
                  <strong>{teamName(team)}</strong>
                  <em>{stats.pts}</em>
                  <small>{stats.gf - stats.gc >= 0 ? "+" : ""}{stats.gf - stats.gc}</small>
                </motion.li>
              );
            })}
          </motion.ol>
        </div>
      </div>
    </div>
  );
}

function ThirdsScreen({
  thirds,
  matches,
  table,
  reducedMotion,
}: {
  thirds: string[];
  matches: Match[];
  table: Record<string, TeamStats>;
  reducedMotion: boolean;
}) {
  return (
    <div className="phase-page phase-page--thirds">
      <div className="phase-copy">
        <span className="phase-kicker">cierre de grupos</span>
        <h2>Los terceros entran por una puerta angosta</h2>
        <p>Ocho equipos sobreviven al corte de la tabla pronosticada y completan el cuadro de dieciseisavos.</p>
      </div>

      <ol className="thirds-race">
        {thirds.map((team, index) => {
          const stats = table[team];
          const group = matches.find((match) => match.home === team || match.away === team)?.group;
          return (
            <motion.li
              key={team}
              initial={reducedMotion ? false : { opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: reducedMotion ? 0 : index * 0.07 }}
            >
              <span>{String(index + 1).padStart(2, "0")}</span>
              <strong>{teamName(team)}</strong>
              <em>Grupo {group}</em>
              <small>{stats.pts} pts · DG {stats.gf - stats.gc >= 0 ? "+" : ""}{stats.gf - stats.gc}</small>
            </motion.li>
          );
        })}
      </ol>
    </div>
  );
}

export function MundialGroups({
  prode,
  matches,
  ranked,
  table,
  thirds,
  knockout,
  prodeCode,
}: {
  prode: Prode;
  matches: Match[];
  ranked: Record<string, string[]>;
  table: Record<string, TeamStats>;
  thirds: string[];
  knockout: KnockoutDraw;
  prodeCode: string;
}) {
  const reducedMotion = useReducedMotionPreference();
  const groupedMatches = useMemo(() => groupMatches(matches), [matches]);
  const screens = useMemo(() => buildScreens(), []);
  const [screenIndex, setScreenIndex] = useState(0);
  const [autoplay, setAutoplay] = useState(false);
  const current = screens[screenIndex] ?? screens[0];
  const activePhase = phaseIndex(current);
  const finalScreenActive = current.kind === "round" && current.round === "final";
  const atmosphereKind = current.kind === "group" || current.kind === "thirds"
    ? "groups"
    : finalScreenActive
      ? "final"
      : "knockout";

  useEffect(() => {
    if (reducedMotion) {
      setScreenIndex(screens.length - 1);
      setAutoplay(false);
    }
  }, [reducedMotion, screens.length]);

  useEffect(() => {
    if (!autoplay || reducedMotion) return;
    const timer = window.setInterval(() => {
      setScreenIndex((index) => {
        const next = Math.min(screens.length - 1, index + 1);
        if (next === screens.length - 1) setAutoplay(false);
        return next;
      });
    }, current.kind === "group" ? 2200 : 2800);
    return () => window.clearInterval(timer);
  }, [autoplay, current.kind, reducedMotion, screens.length]);

  useEffect(() => {
    if (current.kind !== "round" || current.round !== "final" || reducedMotion) return;
    void import("canvas-confetti")
      .then(({ default: confetti }) => {
        confetti({ particleCount: 110, spread: 68, origin: { y: 0.68 } });
      })
      .catch(() => {});
  }, [current, reducedMotion]);

  function goNext() {
    setScreenIndex((index) => Math.min(screens.length - 1, index + 1));
  }

  function skipPhase() {
    const targetPhase = Math.min(phaseLabels.length - 1, activePhase + 1);
    const nextIndex = screens.findIndex((screen) => phaseIndex(screen) >= targetPhase);
    setScreenIndex(nextIndex === -1 ? screens.length - 1 : nextIndex);
  }

  function skipAll() {
    setScreenIndex(screens.length - 1);
    setAutoplay(false);
  }

  function replayFromStart() {
    setAutoplay(false);
    setScreenIndex(0);
  }

  function clearDraftForNewProde() {
    localStorage.removeItem(DRAFT_KEY);
    localStorage.removeItem("prode-mundial-2026:worldRevealState");
  }

  return (
    <main className="world-shell">
      <PhaseAtmosphere kind={atmosphereKind} />
      <header className="world-header">
        <div>
          <p className="eyebrow">Mundial pronosticado de {prode.player}</p>
          <h1>{current.label}</h1>
        </div>
        <nav className="phase-rail" aria-label="Fases">
          {phaseLabels.map((phase, index) => (
            <span className={index === activePhase ? "is-active" : index < activePhase ? "is-done" : ""} key={phase}>
              {phase}
            </span>
          ))}
        </nav>
      </header>

      <section className="world-stage" aria-live="polite">
        <AnimatePresence mode="wait">
          <motion.div
            key={current.kind === "round" ? "knockout-bracket" : `${current.kind}-${current.label}`}
            variants={screenVariants}
            initial={reducedMotion ? false : "initial"}
            animate="enter"
            exit={reducedMotion ? undefined : "exit"}
            transition={{ duration: reducedMotion ? 0 : 0.42, ease: [0.22, 1, 0.36, 1] }}
          >
            {current.kind === "group" ? (
              <GroupScreen
                group={current.group}
                matches={groupedMatches[current.group] ?? []}
                prode={prode}
                ranked={ranked}
                table={table}
                thirds={thirds}
                reducedMotion={reducedMotion}
              />
            ) : null}

            {current.kind === "thirds" ? (
              <ThirdsScreen
                thirds={thirds}
                matches={matches}
                table={table}
                reducedMotion={reducedMotion}
              />
            ) : null}

            {current.kind === "round" ? (
              <KnockoutBracket
                knockout={knockout}
                revealedRound={current.round}
                reducedMotion={reducedMotion}
              />
            ) : null}
          </motion.div>
        </AnimatePresence>
      </section>

      {finalScreenActive ? (
        <div className="final-actions" aria-label="Acciones finales">
          <button className="button button--secondary" type="button" onClick={replayFromStart}>
            Reproducir desde el grupo A
          </button>
          <Link className="button button--ghost" href={`/prode?p=${encodeURIComponent(prodeCode)}`}>
            Editar resultados
          </Link>
          <Link className="button button--primary" href="/prode?new=1" onClick={clearDraftForNewProde}>
            Armar otro mundial
          </Link>
        </div>
      ) : null}

      <div className="sticky-controls">
        <button className="button button--secondary" type="button" onClick={() => setAutoplay((value) => !value)}>
          {autoplay ? "Pausar" : "Autoplay"}
        </button>
        <button className="button button--primary" type="button" onClick={goNext} disabled={screenIndex === screens.length - 1}>
          Siguiente
        </button>
        <button className="button button--ghost" type="button" onClick={skipPhase} disabled={screenIndex === screens.length - 1}>
          Saltear fase
        </button>
        <button className="button button--ghost" type="button" onClick={skipAll}>
          Saltear todo
        </button>
      </div>
    </main>
  );
}

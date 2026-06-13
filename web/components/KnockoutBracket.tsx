"use client";

import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { FINAL, QF, R16, SF, type KnockoutDefinition } from "@/lib/bracket";
import type { DrawnMatch, KnockoutDraw } from "@/lib/draw";
import { ES } from "@/lib/teams";
import { TrophyVisual } from "@/components/VisualBackdrop";

export type RoundKey = "r32" | "r16" | "qf" | "sf" | "final";

export const roundNames: Record<RoundKey, { label: string; phase: string }> = {
  r32: { label: "Dieciseisavos de final", phase: "16avos" },
  r16: { label: "Octavos de final", phase: "8vos" },
  qf: { label: "Cuartos de final", phase: "4tos" },
  sf: { label: "Semifinales", phase: "Semis" },
  final: { label: "Final", phase: "Final" },
};

const ROUND_ORDER: RoundKey[] = ["r32", "r16", "qf", "sf", "final"];

// Columnas del grid de 17 tracks: partido|conector|... con el centro en la 9.
const MATCH_COL: Record<"left" | "right", Record<Exclude<RoundKey, "final">, number>> = {
  left: { r32: 1, r16: 3, qf: 5, sf: 7 },
  right: { r32: 17, r16: 15, qf: 13, sf: 11 },
};

const CONN_COL: Record<"left" | "right", Record<Exclude<RoundKey, "r32">, number>> = {
  left: { r16: 2, qf: 4, sf: 6, final: 8 },
  right: { r16: 16, qf: 14, sf: 12, final: 10 },
};

const ROW_SPAN: Record<Exclude<RoundKey, "final">, number> = { r32: 2, r16: 4, qf: 8, sf: 16 };

const CONN_CHIP: Record<Exclude<RoundKey, "r32">, string> = {
  r16: "8vos",
  qf: "4tos",
  sf: "Semis",
  final: "Final",
};

type Side = "left" | "right";

type TieEntry = {
  match: DrawnMatch;
  round: RoundKey;
  roundIndex: number;
  side: Side;
  wingIndex: number;
  rowStart: number;
  rowSpan: number;
  col: number;
};

type ConnEntry = {
  key: string;
  childRound: Exclude<RoundKey, "r32">;
  childRoundIndex: number;
  side: Side;
  wingIndex: number;
  rowStart: number;
  rowSpan: number;
  col: number;
  single: boolean;
};

type Layout = {
  ties: TieEntry[];
  conns: ConnEntry[];
  final: DrawnMatch;
};

function buildBracketLayout(knockout: KnockoutDraw): Layout {
  const byN = new Map<number, DrawnMatch>();
  for (const round of ROUND_ORDER) {
    for (const match of knockout[round]) byN.set(match.n, match);
  }

  const defByN = new Map<number, KnockoutDefinition>();
  for (const def of [...R16, ...QF, ...SF, FINAL]) defByN.set(def.n, def);

  function feeders(numbers: number[]) {
    return numbers.flatMap((n) => {
      const def = defByN.get(n);
      if (!def) throw new Error(`Missing knockout definition for match ${n}`);
      return [def.homeFrom, def.awayFrom];
    });
  }

  // Cada ala se deriva del árbol homeFrom/awayFrom, nunca de rangos hardcodeados.
  function wing(sfNumber: number, side: Side): { ties: TieEntry[]; conns: ConnEntry[] } {
    const perRound: Record<Exclude<RoundKey, "final">, number[]> = {
      sf: [sfNumber],
      qf: feeders([sfNumber]),
      r16: feeders(feeders([sfNumber])),
      r32: feeders(feeders(feeders([sfNumber]))),
    };

    const ties: TieEntry[] = [];
    const conns: ConnEntry[] = [];

    for (const round of ["r32", "r16", "qf", "sf"] as const) {
      const span = ROW_SPAN[round];
      perRound[round].forEach((n, wingIndex) => {
        const match = byN.get(n);
        if (!match) throw new Error(`Missing drawn match ${n}`);
        ties.push({
          match,
          round,
          roundIndex: ROUND_ORDER.indexOf(round),
          side,
          wingIndex,
          rowStart: wingIndex * span + 1,
          rowSpan: span,
          col: MATCH_COL[side][round],
        });
        if (round !== "r32") {
          conns.push({
            key: `conn-${n}`,
            childRound: round,
            childRoundIndex: ROUND_ORDER.indexOf(round),
            side,
            wingIndex,
            rowStart: wingIndex * span + 1,
            rowSpan: span,
            col: CONN_COL[side][round],
            single: false,
          });
        }
      });
    }

    conns.push({
      key: `conn-final-${side}`,
      childRound: "final",
      childRoundIndex: ROUND_ORDER.indexOf("final"),
      side,
      wingIndex: 0,
      rowStart: 1,
      rowSpan: 16,
      col: CONN_COL[side].final,
      single: true,
    });

    return { ties, conns };
  }

  const left = wing(FINAL.homeFrom, "left");
  const right = wing(FINAL.awayFrom, "right");
  const final = byN.get(FINAL.n);
  if (!final) throw new Error(`Missing final match ${FINAL.n}`);

  // Orden DOM ascendente por número de partido: en mobile la lista queda 73→88.
  const ties = [...left.ties, ...right.ties].sort((a, b) => a.match.n - b.match.n);

  return { ties, conns: [...left.conns, ...right.conns], final };
}

function teamName(team: string) {
  return ES[team] ?? team;
}

function parseScore(score: string) {
  const penalties = score.includes("pen");
  const [homeGoals, awayGoals] = score.split(" ")[0].split("-");
  return { homeGoals, awayGoals, penalties };
}

type TieStatus = "resolved" | "named" | "hidden";

function TeamBar({
  team,
  goals,
  status,
  isWinner,
  isLoser,
  penalties,
  animateName,
  nameDelay,
  side,
}: {
  team: string;
  goals: string | null;
  status: TieStatus;
  isWinner: boolean;
  isLoser: boolean;
  penalties: boolean;
  animateName: boolean;
  nameDelay: number;
  side: Side | "center";
}) {
  const named = status !== "hidden";
  const className = [
    "ko-team",
    isWinner ? "is-winner" : "",
    isLoser ? "is-loser" : "",
    named ? "" : "is-placeholder",
  ].filter(Boolean).join(" ");
  const fromX = side === "left" ? -10 : side === "right" ? 10 : 0;

  return (
    <div className={className}>
      <span aria-hidden className="ko-team__glow" />
      <motion.span
        animate={{ opacity: 1, x: 0 }}
        className="ko-team__name"
        initial={animateName && named ? { opacity: 0, x: fromX } : false}
        key={`${named ? team : "tbd"}`}
        transition={{ delay: nameDelay, duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
      >
        {named ? teamName(team) : "Por definirse"}
      </motion.span>
      <b>{goals ?? "–"}{isWinner && penalties ? "ᵖ" : ""}</b>
    </div>
  );
}

function KnockoutTie({
  entry,
  status,
  active,
  animateRound,
  animateNames,
  side,
}: {
  entry: { match: DrawnMatch; round: RoundKey; wingIndex: number; rowStart: number; rowSpan: number; col: number };
  status: TieStatus;
  active: boolean;
  animateRound: boolean;
  animateNames: boolean;
  side: Side | "center";
}) {
  const { match } = entry;
  const resolved = status === "resolved";
  const { homeGoals, awayGoals, penalties } = parseScore(match.score);
  const revealDelay = animateRound ? 0.1 + entry.wingIndex * 0.055 : 0;
  const nameDelay = animateNames ? 0.3 + entry.wingIndex * 0.05 : 0;

  const style = {
    "--gr": `${entry.rowStart} / span ${entry.rowSpan}`,
    "--gc": entry.col,
    "--reveal-delay": `${revealDelay}s`,
  } as CSSProperties;

  return (
    <div
      className="ko-match"
      data-active={active || undefined}
      data-round={entry.round}
      data-side={side}
      style={style}
    >
      <span aria-hidden className="ko-match__tag">#{match.n} · {match.p}%</span>
      <TeamBar
        animateName={animateNames}
        goals={resolved ? homeGoals : null}
        isLoser={resolved && match.winner !== match.home}
        isWinner={resolved && match.winner === match.home}
        nameDelay={nameDelay}
        penalties={penalties}
        side={side}
        status={status}
        team={match.home}
      />
      <TeamBar
        animateName={animateNames}
        goals={resolved ? awayGoals : null}
        isLoser={resolved && match.winner !== match.away}
        isWinner={resolved && match.winner === match.away}
        nameDelay={nameDelay + 0.04}
        penalties={penalties}
        side={side}
        status={status}
        team={match.away}
      />
      <small className="ko-match__meta">
        {resolved ? `${teamName(match.winner)} avanza · ${match.score} · ${match.p}%` : `Partido ${match.n} · por jugarse`}
      </small>
    </div>
  );
}

// Tarjeta a foco completo de un cruce (carrusel mobile, un partido a la vez).
function FocusCard({ match }: { match: DrawnMatch }) {
  const { homeGoals, awayGoals, penalties } = parseScore(match.score);
  const homeWins = match.winner === match.home;
  return (
    <article className="ko-fcard">
      <div className={`ko-fteam${homeWins ? " is-winner" : " is-loser"}`}>
        <span>{teamName(match.home)}</span>
        <b>{homeGoals}{penalties && homeWins ? "ᵖ" : ""}</b>
      </div>
      <span className="ko-fvs">vs</span>
      <div className={`ko-fteam${homeWins ? " is-loser" : " is-winner"}`}>
        <span>{teamName(match.away)}</span>
        <b>{awayGoals}{penalties && !homeWins ? "ᵖ" : ""}</b>
      </div>
      <p className="ko-fmeta">{teamName(match.winner)} avanza · {match.score} · {match.p}%</p>
    </article>
  );
}

export function KnockoutBracket({
  knockout,
  revealedRound,
  reducedMotion,
}: {
  knockout: KnockoutDraw;
  revealedRound: RoundKey;
  reducedMotion: boolean;
}) {
  const layout = useMemo(() => buildBracketLayout(knockout), [knockout]);
  const revealedIndex = ROUND_ORDER.indexOf(revealedRound);
  const focusRef = useRef<HTMLDivElement | null>(null);
  const [matchIdx, setMatchIdx] = useState(0);

  // Mobile: al cambiar de ronda, volver al primer cruce del carrusel a foco.
  useEffect(() => {
    setMatchIdx(0);
    focusRef.current?.scrollTo({ left: 0, behavior: "auto" });
  }, [revealedRound]);

  function onFocusScroll() {
    const track = focusRef.current;
    if (!track || !track.clientWidth) return;
    const idx = Math.round(track.scrollLeft / track.clientWidth);
    setMatchIdx((prev) => (prev === idx ? prev : idx));
  }

  // En el primer paint solo anima la ronda actual si no venimos de reduced-motion;
  // los avances posteriores animan únicamente la ronda recién revelada.
  const prevRevealed = useRef(reducedMotion ? revealedIndex : revealedIndex - 1);
  const animating = !reducedMotion && revealedIndex > prevRevealed.current;

  useEffect(() => {
    prevRevealed.current = revealedIndex;
  }, [revealedIndex]);

  function statusOf(roundIndex: number): TieStatus {
    if (roundIndex <= revealedIndex) return "resolved";
    if (roundIndex === revealedIndex + 1) return "named";
    return "hidden";
  }

  const finalRevealed = revealedRound === "final";
  const finalStatus = statusOf(ROUND_ORDER.indexOf("final"));
  const roundMatches = knockout[revealedRound];

  return (
    <div className={`phase-page phase-page--knockout${finalRevealed ? " is-final" : ""}`}>
      <AnimatePresence mode="wait">
        <motion.div
          animate={{ opacity: 1, y: 0 }}
          className="ko-heading"
          exit={reducedMotion ? undefined : { opacity: 0, y: -10 }}
          initial={reducedMotion ? false : { opacity: 0, y: 12 }}
          key={revealedRound}
          transition={{ duration: reducedMotion ? 0 : 0.32, ease: [0.22, 1, 0.36, 1] }}
        >
          <span className="phase-kicker">{roundNames[revealedRound].phase}</span>
          <p>
            {finalRevealed
              ? `${teamName(knockout.champion)} levanta la copa.`
              : "Eliminatoria sorteada desde tu bracket pronosticado. Mismo link, mismo destino."}
          </p>
        </motion.div>
      </AnimatePresence>

      <div aria-label="Cuadro de eliminatorias" className="ko-bracket" role="group">
        {layout.ties.map((entry) => (
          <KnockoutTie
            active={entry.round === revealedRound}
            animateNames={animating && entry.roundIndex === revealedIndex + 1}
            animateRound={animating && entry.roundIndex === revealedIndex}
            entry={entry}
            key={entry.match.n}
            side={entry.side}
            status={statusOf(entry.roundIndex)}
          />
        ))}

        {layout.conns.map((conn) => {
          const lit = revealedIndex >= conn.childRoundIndex - 1;
          const litDelay = animating && conn.childRoundIndex === revealedIndex + 1
            ? 0.34 + conn.wingIndex * 0.06
            : 0;
          const style = {
            "--gr": `${conn.rowStart} / span ${conn.rowSpan}`,
            "--gc": conn.col,
            "--lit-delay": `${litDelay}s`,
          } as CSSProperties;
          return (
            <div
              className={`ko-conn${conn.single ? " ko-conn--single" : ""}${lit ? " is-lit" : ""}`}
              data-side={conn.side}
              key={conn.key}
              style={style}
            >
              <span aria-hidden className="ko-conn__line" />
              <span aria-hidden className="ko-conn__line ko-conn__line--lit" />
              <span className="ko-chip">{CONN_CHIP[conn.childRound]}</span>
            </div>
          );
        })}

        <div
          className={`ko-center${finalRevealed ? " is-champion" : ""}`}
          data-active={finalRevealed || undefined}
        >
          <KnockoutTie
            active={finalRevealed}
            animateNames={animating && ROUND_ORDER.indexOf("final") === revealedIndex + 1}
            animateRound={animating && finalRevealed}
            entry={{ match: layout.final, round: "final", wingIndex: 0, rowStart: 1, rowSpan: 16, col: 9 }}
            side="center"
            status={finalStatus}
          />
          <TrophyVisual />
          {finalRevealed ? (
            <motion.div
              animate={{ opacity: 1, scale: 1 }}
              className="champion-mark"
              initial={reducedMotion || !animating ? false : { opacity: 0, scale: 0.92 }}
              transition={{ delay: reducedMotion ? 0 : 0.45, duration: 0.42 }}
            >
              <span>Campeón</span>
              <strong>{teamName(knockout.champion)}</strong>
            </motion.div>
          ) : null}
        </div>
      </div>

      <div className="ko-focus">
        <div className="ko-focus__head">
          <span className="phase-kicker">{roundNames[revealedRound].label}</span>
          {roundMatches.length > 1 ? (
            <span className="ko-focus__count">{matchIdx + 1}/{roundMatches.length}</span>
          ) : null}
        </div>
        <div
          className="ko-focus__track"
          ref={focusRef}
          onScroll={onFocusScroll}
          role="group"
          aria-label="Cruces de la ronda — deslizá entre partidos"
        >
          {roundMatches.map((match) => (
            <FocusCard key={match.n} match={match} />
          ))}
        </div>
        {roundMatches.length > 1 ? (
          <div className="ko-dots" aria-hidden="true">
            {roundMatches.map((match, i) => (
              <span className={i === matchIdx ? "is-active" : ""} key={match.n} />
            ))}
          </div>
        ) : null}
        {finalRevealed ? (
          <div className="champion-mark">
            <span>Campeón</span>
            <strong>{teamName(knockout.champion)}</strong>
          </div>
        ) : null}
      </div>
    </div>
  );
}

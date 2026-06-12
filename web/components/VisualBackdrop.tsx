import type { CSSProperties } from "react";

type VisualVariant = "home" | "prode" | "world" | "groups" | "knockout" | "ranking" | "og";

const mediaByVariant: Record<VisualVariant, string> = {
  home: "/media/hero-stadium.svg",
  prode: "/media/prode-boardroom.svg",
  world: "/media/world-tunnel.svg",
  groups: "/media/phase-groups.svg",
  knockout: "/media/phase-knockout.svg",
  ranking: "/media/phase-knockout.svg",
  og: "/media/og-default.svg",
};

function mediaStyle(variant: VisualVariant): CSSProperties {
  return {
    "--visual-media": `url("${mediaByVariant[variant]}")`,
  } as CSSProperties;
}

export function VisualBackdrop({
  variant,
  className = "",
}: {
  variant: VisualVariant;
  className?: string;
}) {
  return <div aria-hidden="true" className={`visual-backdrop ${className}`} style={mediaStyle(variant)} />;
}

export function HeroMedia({ variant = "home" }: { variant?: VisualVariant }) {
  return (
    <div aria-hidden="true" className="hero-media" style={mediaStyle(variant)}>
      <div className="hero-media__frame" />
      <div className="hero-media__scan" />
    </div>
  );
}

export function PhaseAtmosphere({ kind }: { kind: "groups" | "knockout" | "final" }) {
  const variant = kind === "groups" ? "groups" : "knockout";
  return (
    <div
      aria-hidden="true"
      className={`phase-atmosphere phase-atmosphere--${kind}`}
      style={mediaStyle(variant)}
    />
  );
}

export function TrophyVisual() {
  return (
    <div aria-hidden="true" className="trophy-visual" style={mediaStyle("world")}>
      <img alt="" src="/media/trophy-generic.svg" />
    </div>
  );
}

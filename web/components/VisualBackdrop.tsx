import type { CSSProperties } from "react";

type VisualVariant = "home" | "prode" | "world" | "groups" | "knockout" | "ranking" | "og";

const mediaByVariant: Record<VisualVariant, string> = {
  home: "/media/hero-stadium.webp",
  prode: "/media/prode-boardroom.webp",
  world: "/media/world-tunnel.webp",
  groups: "/media/phase-groups.webp",
  knockout: "/media/phase-knockout.webp",
  ranking: "/media/phase-knockout.webp",
  og: "/media/og-default.webp",
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
      <img alt="" src="/media/trophy-generic.webp" />
    </div>
  );
}

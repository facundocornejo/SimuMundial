import { ImageResponse } from "next/og";
import { buildR32 } from "@/lib/bracket";
import { getFixture, getProfiles } from "@/lib/data.server";
import { rngFromProde, runKnockout } from "@/lib/draw";
import { orderedMatchIds } from "@/lib/match-order";
import { decodeProde } from "@/lib/prode-codec";
import { validateProde } from "@/lib/prode-validation";
import type { Prode } from "@/lib/types";

export const runtime = "nodejs";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("p");
  const backgroundUrl = new URL("/media/og-default.svg", request.url).toString();
  const [fixture, profiles] = await Promise.all([getFixture(), getProfiles()]);
  const matchIds = orderedMatchIds(fixture.matches);
  let prode: Prode | null = null;

  if (code) {
    try {
      const decoded = decodeProde(code, matchIds);
      const validation = validateProde(decoded, matchIds);
      if (validation.valid) {
        prode = {
          player: validation.player,
          results: decoded.results,
        };
      }
    } catch {}
  }

  const champion = prode
    ? runKnockout(
      buildR32(prode.results, fixture.matches, fixture.fairplay).fixtures,
      profiles.profiles,
      rngFromProde(prode),
    ).champion
    : "Tu campeón";

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          background: "#050911",
          color: "#e8edf8",
          padding: 72,
          fontFamily: "Arial",
          position: "relative",
          overflow: "hidden",
        }}
      >
        <img
          alt=""
          src={backgroundUrl}
          style={{
            position: "absolute",
            inset: 0,
            width: "100%",
            height: "100%",
            objectFit: "cover",
          }}
        />
        <div style={{ position: "absolute", inset: 0, background: "rgba(2, 5, 8, 0.34)" }} />
        <div style={{ color: "#e7b84b", fontSize: 34, fontWeight: 800, position: "relative" }}>
          Prode Mundial 2026
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 24, position: "relative" }}>
          <div style={{ fontSize: 76, fontWeight: 900, lineHeight: 1 }}>
            {prode ? `Mundial pronosticado de ${prode.player}` : "Prode Mundial 2026"}
          </div>
          <div style={{ color: "#fbbf24", fontSize: 54, fontWeight: 900 }}>
            {champion}
          </div>
        </div>
        <div style={{ color: "#c8d4c0", fontSize: 28, position: "relative" }}>
          Grupos, cuadro y destino sorteado desde tu pronóstico
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}

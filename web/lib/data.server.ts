import { access, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import type { FixtureData, Prode, ProfilesData, Score } from "./types";

const root = resolve(process.cwd(), "..");

async function firstExisting(paths: string[]) {
  for (const candidate of paths) {
    try {
      await access(candidate);
      return candidate;
    } catch {}
  }
  return paths[0];
}

async function readJson<T>(relativePath: string): Promise<T> {
  const raw = await readFile(resolve(root, relativePath), "utf8");
  return JSON.parse(raw) as T;
}

async function readDataJson<T>(fileName: string): Promise<T> {
  const filePath = await firstExisting([
    resolve(process.cwd(), "data", fileName),
    resolve(root, "data", fileName),
  ]);
  const raw = await readFile(filePath, "utf8");
  return JSON.parse(raw) as T;
}

export type PredictionsData = {
  predictions: Record<string, { score_pred?: Score; [key: string]: unknown }>;
};

export async function getFixture() {
  return readDataJson<FixtureData>("fixture.json");
}

export async function getProfiles() {
  return readDataJson<ProfilesData>("team_profiles.json");
}

export async function getPredictions() {
  return readDataJson<PredictionsData>("predictions.json");
}

export async function getModelPicks() {
  return readDataJson<Record<string, Score>>("model_picks.json");
}

export async function getFacuProde() {
  return readJson<Prode>("prode/prode_facu.json");
}

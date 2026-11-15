import type { DataSource } from "./DataSource";

let cached: Promise<DataSource> | null = null;

/**
 * Return the data source for this build. `vite build --mode replay` replaces
 * `import.meta.env.MODE` with "replay", so the live branch and its module are removed
 * from the public bundle (checked by `npm run check:replay-bundle`).
 *
 * @returns The memoised data source.
 */
export function getDataSource(): Promise<DataSource> {
  if (cached === null) {
    cached =
      import.meta.env.MODE === "replay"
        ? import("./ReplaySource").then((m) => new m.ReplaySource())
        : import("./LiveSource").then((m) => new m.LiveSource());
  }
  return cached;
}

/** Test hook: forget the memoised source. */
export function resetDataSourceForTests(): void {
  cached = null;
}

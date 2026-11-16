// Checks the replay build in dist/assets (or the folder given as the first argument).
// 1. No JS file may contain the live API path "/api/". The only text ignored is the exact
//    documentation prefix of R3F's own error messages (see IGNORED_DOC_URL).
// 2. At least one JS file must contain "/replay/scenarios": the ReplaySource is really bundled.
//    Without rule 2 the check passes vacuously when the app does not import the data layer.
// A non-replay build fails rule 1 (it bundles LiveSource), which is the negative control.
import fs from "node:fs";
import path from "node:path";

const LIVE_MARKER = "/api/";
// R3F's own error text links its docs (".../react-three-fiber/api/objects#..."); a string, not a live API call.
const IGNORED_DOC_URL = "https://docs.pmnd.rs/react-three-fiber/api/";
const REPLAY_MARKER = "/replay/scenarios";

/**
 * Check a bundle folder.
 *
 * @param {string} dir - Folder with the built `.js` files.
 * @returns {string[]} Problems found; empty when the replay bundle is valid.
 */
export function checkReplayBundle(dir) {
  if (!fs.existsSync(dir)) return [`bundle folder not found: ${dir}`];
  const files = fs.readdirSync(dir).filter((f) => f.endsWith(".js"));
  const text = new Map(files.map((f) => [f, fs.readFileSync(path.join(dir, f), "utf8")]));
  const problems = [];
  const live = files.filter((f) => text.get(f).replaceAll(IGNORED_DOC_URL, "").includes(LIVE_MARKER));
  if (live.length > 0) problems.push(`live API code in replay bundle: ${live.join(", ")}`);
  if (!files.some((f) => text.get(f).includes(REPLAY_MARKER))) {
    problems.push(`no ReplaySource in the bundle (string "${REPLAY_MARKER}" not found)`);
  }
  return problems;
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(import.meta.filename)) {
  const problems = checkReplayBundle(process.argv[2] ?? "dist/assets");
  if (problems.length > 0) {
    for (const p of problems) console.error(p);
    process.exit(1);
  }
  console.log("replay bundle OK");
}

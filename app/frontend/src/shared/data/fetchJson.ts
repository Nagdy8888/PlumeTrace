import { DataSourceError } from "./errors";

/**
 * Say whether a thrown value is an `AbortError` (a `DOMException` is not always an `Error`
 * across realms, so the name is checked on any object).
 *
 * @param error - The thrown value.
 * @returns True for an aborted request.
 */
export function isAbortError(error: unknown): boolean {
  return typeof error === "object" && error !== null && (error as { name?: unknown }).name === "AbortError";
}

/**
 * Fetch a URL and parse the body as JSON.
 *
 * An aborted request re-throws the original `AbortError` (the caller cancelled on purpose).
 * Every other failure becomes a `DataSourceError`: a rejected fetch is `unreachable`, a 404 is
 * `not_found`, any other non-OK status is `unreachable` (the Vite proxy answers 5xx while the
 * backend is down) and a body that is not JSON is `invalid`.
 *
 * @param url - A relative URL (a backend path or a replay file path).
 * @param signal - Optional abort signal.
 * @returns The parsed JSON value (not validated).
 * @throws {DataSourceError} For every failure except an abort.
 */
export async function fetchJson(url: string, signal?: AbortSignal): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(url, { signal, headers: { Accept: "application/json" } });
  } catch (error) {
    if (isAbortError(error)) throw error;
    throw new DataSourceError("unreachable", `Request to ${url} failed`);
  }
  if (response.status === 404) throw new DataSourceError("not_found", `${url} not found`);
  if (!response.ok) throw new DataSourceError("unreachable", `${url} answered ${response.status}`);
  try {
    return await response.json();
  } catch {
    throw new DataSourceError("invalid", `${url} did not return JSON`);
  }
}

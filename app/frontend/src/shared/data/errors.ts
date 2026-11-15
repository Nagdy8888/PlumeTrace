/** Why a data request failed: no server, unknown id, or a malformed file. */
export type DataSourceErrorKind = "unreachable" | "not_found" | "invalid";

/** Error raised by every DataSource method. The UI chooses its message from `kind`. */
export class DataSourceError extends Error {
  readonly kind: DataSourceErrorKind;

  /**
   * @param kind - Failure category.
   * @param message - Developer-facing detail (never shown verbatim to visitors).
   */
  constructor(kind: DataSourceErrorKind, message: string) {
    super(message);
    this.name = "DataSourceError";
    this.kind = kind;
  }
}

// Public API of shared/data. ReplaySource and LiveSource are deliberately NOT exported: they are
// loaded only by getDataSource() so the replay build can drop LiveSource.
export type { DataSource, DataSourceMode } from "./DataSource";
export { DataSourceError } from "./errors";
export type { DataSourceErrorKind } from "./errors";
export { getDataSource, resetDataSourceForTests } from "./getDataSource";
export { useActiveScenario, useScenarioStatus, useScenarioStore } from "./scenarioStore";
export { useCurrentConditions } from "./useCurrentConditions";
export type { CurrentConditions } from "./useCurrentConditions";
export type { LoadStatus, ScenarioState } from "./scenarioStore";

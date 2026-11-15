import { afterEach, describe, expect, it, vi } from "vitest";

import { DataSourceError } from "./errors";
import { LiveSource } from "./LiveSource";

afterEach(() => vi.unstubAllGlobals());

describe("LiveSource id guard", () => {
  it.each(["../x", "s1/../x", "s1_a/b", "S1_Rod_Packing", ""])(
    "rejects %j as not_found without calling fetch",
    async (id) => {
      const fetchMock = vi.fn();
      vi.stubGlobal("fetch", fetchMock);
      const error: unknown = await new LiveSource().loadScenario(id).catch((e: unknown) => e);
      expect(error).toBeInstanceOf(DataSourceError);
      expect(error).toMatchObject({ kind: "not_found" });
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { Panel } from "./Panel";

describe("Panel", () => {
  it("labels its region with the title", () => {
    render(<Panel title="Events">content</Panel>);
    expect(screen.getByRole("region", { name: "Events" })).toHaveTextContent("content");
  });
});

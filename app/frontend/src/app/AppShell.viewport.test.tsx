import { render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "./AppShell";

function stubViewport(narrow: boolean): void {
  vi.stubGlobal("matchMedia", (q: string) => ({
    matches: narrow && q === "(max-width: 767px)",
    media: q,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
  }));
}

afterEach(() => vi.unstubAllGlobals());

describe("AppShell viewport switch", () => {
  it("shows the mobile page on a narrow screen and requests no scenario data", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    stubViewport(true);
    render(<AppShell />);
    expect(screen.getByRole("heading", { level: 1, name: /Methane leak detection/ })).toBeInTheDocument();
    expect(screen.queryByRole("main", { name: "Station view" })).not.toBeInTheDocument();
    expect(fetchMock).not.toHaveBeenCalled();
  });
  it("shows the control room on a wide screen, with the skip link before the top bar", () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("x")));
    stubViewport(false);
    render(<AppShell />);
    const skip = screen.getByRole("link", { name: "Skip to alarms" });
    expect(skip).toHaveAttribute("href", "#alarms-panel");
    const product = screen.getByRole("heading", { level: 1, name: "PlumeTrace" });
    expect(skip.compareDocumentPosition(product) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(document.getElementById("alarms-panel")).not.toBeNull();
    expect(screen.getByRole("main", { name: "Station view" })).toBeInTheDocument();
  });
});

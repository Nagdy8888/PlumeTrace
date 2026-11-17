import "@testing-library/jest-dom/vitest";

import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// jsdom has no layout, so it does not implement scrollIntoView (the equipment list calls it).
Element.prototype.scrollIntoView = () => undefined;
// jsdom has no canvas: its getContext prints "Not implemented" and returns null. Return null quietly,
// so the WebGL 2 check (`hasWebGL2`) finds "no WebGL 2" without console noise (tests can spy on it).
HTMLCanvasElement.prototype.getContext = () => null;

afterEach(() => {
  cleanup();
});

import { Component, type ErrorInfo, type ReactNode } from "react";

/** Props of {@link StationErrorBoundary}. */
export interface StationErrorBoundaryProps {
  /** Shown instead of the children after an error. */
  fallback: ReactNode;
  /** The 3D view. */
  children: ReactNode;
}

interface BoundaryState {
  failed: boolean;
}

/**
 * Catches errors thrown while the 3D view loads or renders (the model fails to load, a shader
 * does not compile) and shows `fallback` instead. The error is logged once with `console.error`.
 */
export class StationErrorBoundary extends Component<StationErrorBoundaryProps, BoundaryState> {
  state: BoundaryState = { failed: false };

  static getDerivedStateFromError(): BoundaryState {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error("station view failed", error, info.componentStack);
  }

  render(): ReactNode {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

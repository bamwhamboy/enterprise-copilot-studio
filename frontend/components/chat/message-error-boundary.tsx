"use client";

import { Component, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
}

/**
 * Wraps each individual message bubble. Without this, a render error
 * thrown by any single message (a malformed citation, an edge case in
 * markdown parsing, etc.) propagates up and unmounts the *entire* chat
 * workspace -- including the input box, which would otherwise just
 * vanish along with everything else. This contains the failure to the
 * one broken message and keeps the rest of the UI (including the
 * input) fully usable.
 */
export class MessageErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: unknown) {
    console.error("Failed to render a chat message:", error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center gap-2 rounded-lg border border-destructive/20 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          <AlertTriangle className="size-3.5 shrink-0" />
          This message couldn&apos;t be displayed.
        </div>
      );
    }
    return this.props.children;
  }
}

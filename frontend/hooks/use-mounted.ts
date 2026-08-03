import { useSyncExternalStore } from "react";

const emptySubscribe = () => () => {};

/**
 * Returns true only once the component has mounted on the client.
 * Useful for theme toggles, portals, or anything reading window/localStorage,
 * without triggering a synchronous setState-in-effect render cascade.
 */
export function useMounted() {
  return useSyncExternalStore(
    emptySubscribe,
    () => true,
    () => false
  );
}

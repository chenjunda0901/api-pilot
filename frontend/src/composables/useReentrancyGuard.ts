import { ref } from 'vue';

/**
 * Prevents re-entrant (double-submit) execution of async functions.
 * Returns an `isRunning` ref and a `guard` wrapper.
 *
 * - `guard(fn)` runs `fn` only when no other guarded call is in flight;
 *   otherwise it resolves to `null`.
 * - `isRunning` reflects whether a guarded call is currently executing.
 */
export function useReentrancyGuard() {
  const isRunning = ref(false);

  async function guard<T>(fn: () => Promise<T>): Promise<T | null> {
    if (isRunning.value) return null;
    isRunning.value = true;
    try {
      return await fn();
    } finally {
      isRunning.value = false;
    }
  }

  return { isRunning, guard };
}

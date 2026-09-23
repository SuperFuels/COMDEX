/*
 * Tessaris renderer stability governor.
 *
 * The desktop UI contains many independently added compatibility patches.
 * Several of them watch the whole document and then update the DOM, which can
 * cause every other watcher to run again.  Others use sub-second maintenance
 * polling for UI that is normally idle.  On a large persisted workspace this
 * feedback can saturate the renderer and, through repeated requests, the local
 * backend.
 *
 * Install one conservative scheduler before the feature bundles load:
 * - coalesce each MutationObserver to at most one callback per 750 ms;
 * - cap legacy repeating timers at five seconds;
 * - cap background visual animation at 20 frames per second;
 * - slow maintenance work while the window is hidden;
 * - expose counters for the Electron startup watchdog and diagnostics.
 *
 * This does not suppress mutations, remove observers, or change one-shot
 * timers.  User-driven handlers therefore remain immediate.
 */
(function installTessarisRendererStabilityGovernor() {
  "use strict";

  if (window.__TESSARIS_RENDERER_STABILITY_INSTALLED__) return;
  window.__TESSARIS_RENDERER_STABILITY_INSTALLED__ = true;

  const NativeMutationObserver = window.MutationObserver;
  const nativeSetInterval = window.setInterval.bind(window);
  const nativeClearInterval = window.clearInterval.bind(window);
  const nativeSetTimeout = window.setTimeout.bind(window);
  const nativeClearTimeout = window.clearTimeout.bind(window);
  const nativeRequestAnimationFrame = window.requestAnimationFrame.bind(window);
  const nativeCancelAnimationFrame = window.cancelAnimationFrame.bind(window);

  const MIN_INTERVAL_MS = 5000;
  const MUTATION_DEBOUNCE_MS = 750;
  const HIDDEN_MUTATION_DEBOUNCE_MS = 2000;
  const FRAME_INTERVAL_MS = 50;
  let nextAnimationRequestId = 1;
  const pendingAnimationFrames = new Map();

  const stats = {
    installedAt: new Date().toISOString(),
    intervalRegistrations: 0,
    clampedIntervals: 0,
    intervalCallbacks: 0,
    observerRegistrations: 0,
    observerSignals: 0,
    observerCallbacks: 0,
    coalescedObserverSignals: 0,
    animationFrameRegistrations: 0,
    animationFrameCallbacks: 0,
    animationFrameCancellations: 0,
  };

  window.__tessarisRendererStabilityStats = stats;

  window.setInterval = function tessarisStableSetInterval(handler, delay, ...args) {
    const requestedDelay = Number.isFinite(Number(delay)) ? Number(delay) : 0;
    const stableDelay = Math.max(requestedDelay, MIN_INTERVAL_MS);
    stats.intervalRegistrations += 1;
    if (stableDelay !== requestedDelay) stats.clampedIntervals += 1;

    const invoke = typeof handler === "function"
      ? function invokeStableInterval() {
          stats.intervalCallbacks += 1;
          return handler(...args);
        }
      : handler;

    return nativeSetInterval(invoke, stableDelay);
  };

  window.clearInterval = function tessarisStableClearInterval(intervalId) {
    return nativeClearInterval(intervalId);
  };

  window.requestAnimationFrame = function tessarisStableRequestAnimationFrame(callback) {
    const requestId = nextAnimationRequestId++;
    stats.animationFrameRegistrations += 1;

    const timeoutId = nativeSetTimeout(() => {
      const pending = pendingAnimationFrames.get(requestId);
      if (!pending) return;
      pending.nativeFrameId = nativeRequestAnimationFrame((timestamp) => {
        if (!pendingAnimationFrames.delete(requestId)) return;
        stats.animationFrameCallbacks += 1;
        callback(timestamp);
      });
    }, document.hidden ? 250 : FRAME_INTERVAL_MS);

    pendingAnimationFrames.set(requestId, { timeoutId, nativeFrameId: null });
    return requestId;
  };

  window.cancelAnimationFrame = function tessarisStableCancelAnimationFrame(requestId) {
    const pending = pendingAnimationFrames.get(requestId);
    if (!pending) return;
    pendingAnimationFrames.delete(requestId);
    nativeClearTimeout(pending.timeoutId);
    if (pending.nativeFrameId !== null) {
      nativeCancelAnimationFrame(pending.nativeFrameId);
    }
    stats.animationFrameCancellations += 1;
  };

  if (typeof NativeMutationObserver === "function") {
    class TessarisStableMutationObserver extends NativeMutationObserver {
      constructor(callback) {
        if (typeof callback !== "function") {
          super(callback);
          return;
        }

        let owner = null;
        let pendingTimer = null;
        let pendingRecords = [];

        super((records) => {
          stats.observerSignals += 1;
          pendingRecords = records;

          if (pendingTimer !== null) {
            stats.coalescedObserverSignals += 1;
            return;
          }

          const delayMs = document.hidden
            ? HIDDEN_MUTATION_DEBOUNCE_MS
            : MUTATION_DEBOUNCE_MS;

          pendingTimer = nativeSetTimeout(() => {
            pendingTimer = null;
            const recordsToDeliver = pendingRecords;
            pendingRecords = [];
            stats.observerCallbacks += 1;
            callback.call(owner, recordsToDeliver, owner);
          }, delayMs);
        });

        owner = this;
        stats.observerRegistrations += 1;
      }
    }

    window.MutationObserver = TessarisStableMutationObserver;
  }

  console.info(
    `[Tessaris] Renderer stability governor active (intervals >= ${MIN_INTERVAL_MS}ms, animations <= ${Math.round(1000 / FRAME_INTERVAL_MS)}fps, mutation debounce ${MUTATION_DEBOUNCE_MS}ms).`,
  );
})();

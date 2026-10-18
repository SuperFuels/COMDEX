(function installAionDesktopPreferences(global) {
  'use strict';
  const policy = global.TessarisDesktopPreferencePolicy;
  if (!policy) throw new Error('TessarisDesktopPreferencePolicy must load before desktop preferences');
  const { isAllowedKey, validateValue } = policy;

  function set(key, value, options = {}) {
    const safeKey = String(key || '');
    if (!isAllowedKey(safeKey)) throw new Error(`Unregistered desktop preference key: ${safeKey}`);
    const encoded = validateValue(safeKey, value);
    if (options.session === true) global.sessionStorage.setItem(safeKey, encoded);
    else global.localStorage.setItem(safeKey, encoded);
    return encoded;
  }

  function remove(key, options = {}) {
    const safeKey = String(key || '');
    if (!isAllowedKey(safeKey)) throw new Error(`Unregistered desktop preference key: ${safeKey}`);
    if (options.session === true) global.sessionStorage.removeItem(safeKey);
    else global.localStorage.removeItem(safeKey);
  }

  global.AionDesktopPreferences = Object.freeze({ isAllowedKey, set, remove });
})(window);

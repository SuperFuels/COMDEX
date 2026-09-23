(function installAionFinanceLightTheme(global) {
  'use strict';

  if (!global.document || global.document.getElementById('aion-finance-light-theme-final')) return;
  const style = global.document.createElement('style');
  style.id = 'aion-finance-light-theme-final';
  style.textContent = `
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"],
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-pilot-stream-header,
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-shared-pilot-role-context,
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-pilot-stream-window {
      background: #ffffff !important;
      color: #102a43 !important;
    }
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-pilot-stream-window::before,
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-pilot-stream-window::after {
      background: #ffffff !important;
    }
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-pilot-stream-header h2,
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-pilot-stream-header p,
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-pilot-stream-message,
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-pilot-stream-message p {
      color: #102a43 !important;
      opacity: 1 !important;
    }
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-pilot-stream-header h2 {
      color: #0f766e !important;
    }
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-pilot-composer-bar,
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-pilot-composer-bar textarea {
      background: #ffffff !important;
      color: #102a43 !important;
      border-color: #b7c8d6 !important;
    }
    html body section.aion-pilot-stream-shell[data-aion-pilot-role="finance"] .aion-pilot-composer-bar textarea::placeholder {
      color: #64748b !important;
      opacity: 1 !important;
    }
  `;
  global.document.head.appendChild(style);
})(window);

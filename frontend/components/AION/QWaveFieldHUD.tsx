// frontend/components/AION/QWaveFieldHUD.tsx
'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';

interface FieldState {
  gravity: number;
  magnetic: number;
  wave_intensity: number;
}

interface ProtonFlow {
  source: string;
  target: string;
  force: number;
}

/**
 * QWaveFieldHUD — DOM-only HUD overlay (no R3F / drei).
 *
 * This can be mounted anywhere (including /sci) without requiring a <Canvas>
 * parent, because it doesn't use @react-three/fiber or @react-three/drei hooks.
 */
export default function QWaveFieldHUD() {
  const [fields, setFields] = useState<FieldState>({
    gravity: 1.0,
    magnetic: 0.5,
    wave_intensity: 1.2,
  });

  const [flows, setFlows] = useState<ProtonFlow[]>([]);
  const [stage, setStage] = useState<number>(0);

  // --- Data fetchers --------------------------------------------------------
  const fetchFieldStates = async () => {
    try {
      const res = await axios.get('/api/aion/engine/qwave/fields');
      const data = res.data || {};
      setFields(data.fields ?? fields);
      setFlows(Array.isArray(data.flows) ? data.flows : []);
      setStage(typeof data.stage === 'number' ? data.stage : 0);
    } catch (err) {
      // Optional: console.warn('QWaveFieldHUD: failed to fetch fields', err);
    }
  };

  useEffect(() => {
    fetchFieldStates();
    const interval = setInterval(fetchFieldStates, 1000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleFieldChange = async (field: keyof FieldState, value: number) => {
    setFields((prev) => ({ ...prev, [field]: value }));
    try {
      await axios.post(`/api/aion/engine/qwave/fields`, { field, value });
    } catch (err) {
      // Optional: console.warn('QWaveFieldHUD: failed to update field', err);
    }
  };

  const advanceStage = async () => {
    try {
      await axios.post('/api/aion/engine/qwave/advance');
      fetchFieldStates();
    } catch (err) {
      // Optional: console.warn('QWaveFieldHUD: failed to advance stage', err);
    }
  };

  // --- Render: fixed DOM overlay -------------------------------------------
  return (
    <div className="pointer-events-auto fixed top-4 right-4 z-50 w-80 bg-black/80 p-4 rounded-lg text-white shadow-lg border border-cyan-500">
      <h2 className="text-lg font-bold mb-2">⚡ QWave Engine Field Control</h2>

      {/* Stage tracker */}
      <div className="flex justify-between items-center mb-4 text-sm">
        <span>
          Engine Stage: <strong>{stage}</strong>
        </span>
        <button
          onClick={advanceStage}
          className="bg-cyan-600 px-2 py-1 rounded text-xs hover:bg-cyan-500"
        >
          Advance ⏩
        </button>
      </div>

      {/* Field sliders */}
      {(['gravity', 'magnetic', 'wave_intensity'] as (keyof FieldState)[]).map(
        (field) => (
          <div key={field} className="mb-3">
            <label className="block text-sm mb-1 capitalize">
              {field.replace('_', ' ')}
            </label>
            <input
              type="range"
              min="0"
              max="5"
              step="0.1"
              value={fields[field]}
              onChange={(e) =>
                handleFieldChange(field, parseFloat(e.target.value))
              }
              className="w-full"
            />
            <span className="text-xs">{fields[field].toFixed(2)}</span>
          </div>
        )
      )}

      {/* Proton flow "log" */}
      <div className="mt-4">
        <h3 className="text-sm font-bold mb-2">Proton Flow Routes:</h3>
        <div className="bg-black/60 p-2 rounded text-xs h-28 overflow-y-auto border border-cyan-700">
          {flows.length > 0 ? (
            flows.map((f, i) => (
              <div key={i} className="flex justify-between">
                <span>
                  🔄 {f.source} ➡ {f.target}
                </span>
                <span className="text-cyan-400">{f.force.toFixed(3)}</span>
              </div>
            ))
          ) : (
            <p className="text-gray-400">No active flows</p>
          )}
        </div>
      </div>
    </div>
  );
}
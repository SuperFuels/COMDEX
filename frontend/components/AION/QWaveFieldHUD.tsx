'use client';

import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Html } from '@react-three/drei';

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

export default function QWaveFieldHUD() {
  const [fields, setFields] = useState<FieldState>({
    gravity: 1.0,
    magnetic: 0.5,
    wave_intensity: 1.2,
  });

  const [flows, setFlows] = useState<ProtonFlow[]>([]);
  const [stage, setStage] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(false);

  // Fetch field states + proton flow updates
  const fetchFieldStates = async () => {
    const res = await axios.get('/api/aion/engine/qwave/fields');
    setFields(res.data.fields);
    setFlows(res.data.flows || []);
    setStage(res.data.stage || 0);
  };

  useEffect(() => {
    fetchFieldStates();
    const interval = setInterval(fetchFieldStates, 1000); // poll every second
    return () => clearInterval(interval);
  }, []);

  const handleFieldChange = async (field: keyof FieldState, value: number) => {
    setFields((prev) => ({ ...prev, [field]: value }));
    await axios.post(`/api/aion/engine/qwave/fields`, { field, value });
  };

  const advanceStage = async () => {
    await axios.post('/api/aion/engine/qwave/advance');
    fetchFieldStates();
  };

  return (
    <Html fullscreen>
      <div className="absolute top-4 right-4 w-80 bg-black/80 p-4 rounded-lg text-white shadow-lg border border-cyan-500">
        <h2 className="text-lg font-bold mb-2">⚡ QWave Engine Field Control</h2>

        {/* Stage Tracker */}
        <div className="flex justify-between items-center mb-4">
          <span>Engine Stage: <strong>{stage}</strong></span>
          <button
            onClick={advanceStage}
            className="bg-cyan-600 px-2 py-1 rounded text-xs hover:bg-cyan-500"
          >
            Advance ⏩
          </button>
        </div>

        {/* Field Sliders */}
        {(['gravity', 'magnetic', 'wave_intensity'] as (keyof FieldState)[]).map((field) => (
          <div key={field} className="mb-3">
            <label className="block text-sm mb-1 capitalize">{field.replace('_', ' ')}</label>
            <input
              type="range"
              min="0"
              max="5"
              step="0.1"
              value={fields[field]}
              onChange={(e) => handleFieldChange(field, parseFloat(e.target.value))}
              className="w-full"
            />
            <span className="text-xs">{fields[field].toFixed(2)}</span>
          </div>
        ))}

        {/* Proton Flow Visualization */}
        <div className="mt-4">
          <h3 className="text-sm font-bold mb-2">Proton Flow Routes:</h3>
          <div className="bg-black/60 p-2 rounded text-xs h-28 overflow-y-auto border border-cyan-700">
            {flows.length > 0 ? (
              flows.map((f, i) => (
                <div key={i} className="flex justify-between">
                  <span>🔄 {f.source} ➡ {f.target}</span>
                  <span className="text-cyan-400">{f.force.toFixed(3)}</span>
                </div>
              ))
            ) : (
              <p className="text-gray-400">No active flows</p>
            )}
          </div>
        </div>
      </div>
    </Html>
  );
}
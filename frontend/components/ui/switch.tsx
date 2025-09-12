// frontend/components/ui/switch.tsx
import React from 'react';

export const Switch = ({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: () => void;
}) => {
  return (
    <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span>{checked ? 'On' : 'Off'}</span>
    </label>
  );
};
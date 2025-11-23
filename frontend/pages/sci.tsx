// frontend/pages/sci.tsx
'use client';

import React from 'react';
import IDE from '../sci/pages/IDE';
import { QFCFocusProvider } from '@/components/QuantumField/qfc_focus_context';

export default function SciPage() {
  return (
    <QFCFocusProvider>
      <IDE />
    </QFCFocusProvider>
  );
}
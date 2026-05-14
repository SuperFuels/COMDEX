// frontend/components/QuantumField/qfc_focus_context.tsx
'use client';

// Just re-export the canonical hook + provider so everyone uses the SAME context.
export { QFCFocusProvider, useQFCFocus } from '@/hooks/useQFCFocus';
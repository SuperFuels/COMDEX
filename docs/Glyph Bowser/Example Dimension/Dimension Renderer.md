
// frontend/components/Dimensions/DimensionRenderer.tsx
export default function DimensionRenderer({ containerId }: { containerId: string }) {
  return (
    <div className="p-6 text-sm text-muted-foreground">
      <div className="rounded-2xl border border-white/10 p-6">
        <div className="text-xl mb-2">Dimension: {containerId}</div>
        <p>This container uses the default renderer. Special UI not registered.</p>
      </div>
    </div>
  );
}
import dynamic from "next/dynamic";
import React from "react";

const GlyphNetClient = dynamic(() => import("@glyphnet/NextGlyphnetApp"), {
  ssr: false,
});

class GlyphNetErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; msg?: string }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(err: any) {
    return { hasError: true, msg: String(err?.message || err) };
  }
  componentDidCatch(err: any) {
    console.error("[GlyphNet] crash:", err);
  }
  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 20, fontFamily: "ui-monospace, monospace" }}>
          <div style={{ fontWeight: 700 }}>GlyphNet crashed</div>
          <div style={{ marginTop: 8, opacity: 0.8 }}>
            {this.state.msg || "Unknown error"}
          </div>
          <div style={{ marginTop: 12, fontSize: 12, opacity: 0.7 }}>
            Open DevTools → Console for stack trace.
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function GlyphNetPage() {
  return (
    <GlyphNetErrorBoundary>
      <GlyphNetClient />
    </GlyphNetErrorBoundary>
  );
}
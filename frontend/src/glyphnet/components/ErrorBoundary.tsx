import React from "react";

type Props = {
  title?: string;
  onReset?: () => void;
  children: React.ReactNode;
};

type State = {
  hasError: boolean;
  errorMsg: string | null;
};

export default class ErrorBoundary extends React.Component<Props, State> {
  state: State = { hasError: false, errorMsg: null };

  static getDerivedStateFromError(err: any) {
    return {
      hasError: true,
      errorMsg: String(err?.message || err || "Unknown error"),
    };
  }

  componentDidCatch(err: any, info: any) {
    // keep logs for devtools debugging
    // eslint-disable-next-line no-console
    console.error("[ErrorBoundary] panel crashed:", err, info);
  }

  handleReset = () => {
    this.setState({ hasError: false, errorMsg: null });
    this.props.onReset?.();
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div
        style={{
          borderRadius: 12,
          border: "1px solid #fecaca",
          background: "#fff1f2",
          padding: 12,
          color: "#7f1d1d",
        }}
      >
        <div style={{ fontSize: 12, fontWeight: 700 }}>
          {this.props.title || "Panel crashed"}
        </div>

        <div style={{ marginTop: 6, fontSize: 11, color: "#991b1b" }}>
          <code>{this.state.errorMsg}</code>
        </div>

        <button
          type="button"
          onClick={this.handleReset}
          style={{
            marginTop: 10,
            padding: "6px 10px",
            borderRadius: 999,
            border: "1px solid #7f1d1d",
            background: "#7f1d1d",
            color: "#fff",
            fontSize: 11,
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Reset panel
        </button>
      </div>
    );
  }
}
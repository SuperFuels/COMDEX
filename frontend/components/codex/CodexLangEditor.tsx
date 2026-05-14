// 📁 frontend/components/Codex/CodexLangEditor.tsx

import React, { useEffect, useRef } from "react";
import Editor from "@monaco-editor/react";

type Props = {
  value: string;
  onChange: (val: string) => void;
};

export default function CodexLangEditor({ value, onChange }: Props) {
  const editorRef = useRef<any>(null);

  const handleEditorDidMount = (editor: any) => {
    editorRef.current = editor;
  };

  return (
    <div className="border border-cyan-500 rounded-md overflow-hidden">
      <Editor
        height="200px"
        defaultLanguage="plaintext"
        value={value}
        onChange={(val) => onChange(val || "")}
        onMount={handleEditorDidMount}
        theme="vs-dark"
        options={{
          fontSize: 14,
          minimap: { enabled: false },
          wordWrap: "on",
          scrollBeyondLastLine: false,
        }}
      />
    </div>
  );
}
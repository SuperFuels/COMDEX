import * as vscode from "vscode";

const CHEATSHEET: Record<string, string> = {
  "⊕": "superposition — combine/merge",
  "μ": "measurement (collapse) — stabilize selection",
  "↔": "entanglement link — correlate fields",
  "⟲": "resonance — feedback / sustain",
  "π": "projection — observable mapping",

  "∧": "logical AND",
  "∨": "logical OR",
  "¬": "logical NOT",
  "≔": "definition / assignment",
  "≟": "equivalence test",
  "⟶": "arrow / lambda",
  "≠": "not equal",
  "≡": "equivalence",
  "∈": "set membership",
  "≤": "less-or-equal",
  "≥": "greater-or-equal",

  "＋": "add (reserved arithmetic)",
  "−": "subtract (reserved arithmetic)",
  "∕": "divide (reserved arithmetic)",
  "＾": "power (reserved arithmetic)",

  "∶": "ratio/typed separator",
  "·": "dot (access/spacing)",
  "‚": "thin comma",
  "⁏": "statement separator"
};

const OPEN = new Set(["⟮", "⟦", "⦃", "(", "[", "{"]);
const CLOSE = new Set(["⟯", "⟧", "⦄", ")", "]", "}"]);
const PAIRS: Record<string, string> = { "⟮": "⟯", "⟦": "⟧", "⦃": "⦄", "(": ")", "[": "]", "{": "}" };

export function activate(ctx: vscode.ExtensionContext) {
  // Hover provider
  ctx.subscriptions.push(
    vscode.languages.registerHoverProvider("photon", {
      provideHover(document: vscode.TextDocument, position: vscode.Position): vscode.ProviderResult<vscode.Hover> {
        const range = document.getWordRangeAtPosition(position, /[⊕μ↔⟲π≔≟⟶∧∨]/);
        if (!range) return;
        const ch = document.getText(range);
        const info = CHEATSHEET[ch];
        if (!info) return;
        return new vscode.Hover([
          new vscode.MarkdownString(`**${ch}** — ${info}`),
          new vscode.MarkdownString("See: _Operator cheatsheet_ in project docs for laws & examples.")
        ]);
      }
    })
  );

  // Diagnostics: highlight unmatched glyph brackets
  const diag = vscode.languages.createDiagnosticCollection("photon");
  ctx.subscriptions.push(diag);

  const runDiagnostics = (doc: vscode.TextDocument) => {
    if (
      doc.languageId !== "photon" ||
      !vscode.workspace.getConfiguration("photon").get<boolean>("enableDiagnostics", true)
    ) {
      diag.delete(doc.uri);
      return;
    }

    const text = doc.getText();
    const stack: Array<{ ch: string; offset: number }> = [];
    const problems: vscode.Diagnostic[] = [];

    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (OPEN.has(c)) {
        stack.push({ ch: c, offset: i });
      } else if (CLOSE.has(c)) {
        if (stack.length === 0) {
          const range = new vscode.Range(doc.positionAt(i), doc.positionAt(i + 1));
          problems.push(new vscode.Diagnostic(range, `Unmatched closing '${c}'`, vscode.DiagnosticSeverity.Warning));
        } else {
          const top = stack.pop()!;
          const expected = PAIRS[top.ch];
          if (c !== expected) {
            const a = new vscode.Range(doc.positionAt(top.offset), doc.positionAt(top.offset + 1));
            problems.push(new vscode.Diagnostic(a, `Expected '${expected}' to match here`, vscode.DiagnosticSeverity.Warning));
            const b = new vscode.Range(doc.positionAt(i), doc.positionAt(i + 1));
            problems.push(new vscode.Diagnostic(b, `Got '${c}' (mismatched pair)`, vscode.DiagnosticSeverity.Warning));
          }
        }
      }
    }

    for (const leftover of stack) {
      const range = new vscode.Range(doc.positionAt(leftover.offset), doc.positionAt(leftover.offset + 1));
      problems.push(new vscode.Diagnostic(range, `Unclosed '${leftover.ch}'`, vscode.DiagnosticSeverity.Warning));
    }

    diag.set(doc.uri, problems);
  };

  ctx.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument(runDiagnostics),
    vscode.workspace.onDidChangeTextDocument((e: vscode.TextDocumentChangeEvent) => runDiagnostics(e.document)),
    vscode.workspace.onDidCloseTextDocument((doc: vscode.TextDocument) => diag.delete(doc.uri))
  );

  // Run once for currently active editor
  if (vscode.window.activeTextEditor) {
    runDiagnostics(vscode.window.activeTextEditor.document);
  }
}

export function deactivate() {}
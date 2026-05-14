/* global acquireVsCodeApi */
const vscode = require('vscode');

const OP_DOCS = {
  "⊕": "**⊕ superposition** — combine waves/symbols without collapse.\n\n_Usage:_ `⊕(a, b)`",
  "μ": "**μ measurement** — deterministic collapse to stable modes.\n\n_Usage:_ `μ(x)`",
  "↔": "**↔ entanglement** — bind two domains into a shared state.\n\n_Usage:_ `↔(A, B)`",
  "⟲": "**⟲ resonance** — reinforce or recycle phase; stabilization.\n\n_Usage:_ `⟲(x)`",
  "π": "**π projection** — map resonance to observer/percept.\n\n_Usage:_ `π[x]`",
  "≔": "**≔ define** — definition/alias binding.",
  "≟": "**≟ compare** — equivalence/comparison (safe).",
  "⟶": "**⟶ implies** — arrow/flow.",
  "∧": "**∧ and** — logical conjunction.",
  "∨": "**∨ or** — logical disjunction."
};

const OPENERS = ["⟮","⟦","⦃","(", "[", "{"];
const CLOSERS = ["⟯","⟧","⦄",")", "]", "}"];
const PAIRS = { "⟮":"⟯", "⟦":"⟧", "⦃":"⦄", "(":")", "[":"]", "{":"}" };

function activate(context) {
  // Hover provider
  context.subscriptions.push(
    vscode.languages.registerHoverProvider('photon', {
      provideHover(doc, pos) {
        const range = doc.getWordRangeAtPosition(
          pos,
          /[⊕μ↔⟲π≔≟⟶∧∨]/u
        );
        if (!range) return;
        const sym = doc.getText(range);
        const md = OP_DOCS[sym];
        if (!md) return;
        return new vscode.Hover(new vscode.MarkdownString(md));
      }
    })
  );

  // Cheatsheet command
  context.subscriptions.push(
    vscode.commands.registerCommand('photon.showCheatsheet', async () => {
      const md = [
        '# Photon Operator Cheatsheet',
        '',
        'Symbol | Name | Sketch',
        '---|---|---',
        '⊕ | superposition | `⊕(a, b)`',
        'μ | measurement | `μ(x)`',
        '↔ | entanglement | `↔(A, B)`',
        '⟲ | resonance | `⟲(x)`',
        'π | projection | `π[x]`',
        '≔ | define | `name ≔ expr`',
        '≟ | compare | `a ≟ b`',
        '⟶ | implies | `A ⟶ B`',
        '∧ / ∨ | and / or | `A ∧ B`, `A ∨ B`',
        '',
        'Brackets: ⟮ ⟯, ⟦ ⟧, ⦃ ⦄ (auto-close).'
      ].join('\n');
      const doc = await vscode.workspace.openTextDocument({ content: md, language: 'markdown' });
      await vscode.window.showTextDocument(doc, vscode.ViewColumn.Beside);
    })
  );

  // Diagnostics: unpaired brackets
  const diags = vscode.languages.createDiagnosticCollection('photon');
  context.subscriptions.push(diags);

  function refreshDiagnostics(doc) {
    if (doc.languageId !== 'photon') return;
    const text = doc.getText();
    const stack = [];
    const problems = [];

    for (let i = 0, off = 0; i < text.length; i++) {
      const ch = text[i];
      if (OPENERS.includes(ch)) {
        stack.push({ ch, idx: i });
      } else if (CLOSERS.includes(ch)) {
        if (stack.length === 0) {
          const rng = new vscode.Range(doc.positionAt(i), doc.positionAt(i + 1));
          problems.push(new vscode.Diagnostic(rng, `Unmatched closing '${ch}'`, vscode.DiagnosticSeverity.Warning));
        } else {
          const { ch: open, idx } = stack.pop();
          const expect = PAIRS[open];
          if (ch !== expect) {
            const rng = new vscode.Range(doc.positionAt(i), doc.positionAt(i + 1));
            problems.push(new vscode.Diagnostic(rng, `Mismatched '${open}' … expected '${expect}', got '${ch}'`, vscode.DiagnosticSeverity.Warning));
          }
        }
      }
      off++;
    }

    while (stack.length) {
      const { ch: open, idx } = stack.pop();
      const rng = new vscode.Range(doc.positionAt(idx), doc.positionAt(idx + 1));
      problems.push(new vscode.Diagnostic(rng, `Unclosed '${open}'`, vscode.DiagnosticSeverity.Warning));
    }

    diags.set(doc.uri, problems);
  }

  // Wire doc events
  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument(refreshDiagnostics),
    vscode.workspace.onDidChangeTextDocument(e => refreshDiagnostics(e.document)),
    vscode.workspace.onDidCloseTextDocument(doc => diags.delete(doc.uri))
  );

  // Initial pass for already-open docs
  vscode.workspace.textDocuments.forEach(refreshDiagnostics);
}

function deactivate() {}

module.exports = { activate, deactivate };
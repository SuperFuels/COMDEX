// tools/photon-js/src/types/tree-sitter.d.ts

declare module "tree-sitter" {
  export default class Parser {
    setLanguage(lang: any): void;
    parse(input: string): Tree;
  }

  export class Point {
    row: number;
    column: number;
  }

  export class Tree {
    rootNode: SyntaxNode;
  }

  export interface SyntaxNode {
    type: string;
    text: string;
    startIndex: number;
    endIndex: number;
    childCount: number;
    children: SyntaxNode[];
    namedChildren: SyntaxNode[];
    parent: SyntaxNode | null;
    child(i: number): SyntaxNode | null;
    walk(): any; // you can refine to a TreeCursor shape later
  }
}

declare module "tree-sitter-javascript" {
  const lang: any;             // a Language object
  export default lang;         // use: import JavaScript from "tree-sitter-javascript";
}

declare module "tree-sitter-typescript" {
  const typescript: any;       // a Language object
  const tsx: any;              // a Language object
  export { typescript, tsx };  // use: import { typescript } from "tree-sitter-typescript";
}
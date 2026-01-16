// frontend/components/MDXComponents.tsx
"use client";

import type { MDXComponents } from "mdx/types";

export const mdxComponents: MDXComponents = {
  h1: (props) => <h1 className="text-4xl font-bold tracking-tight text-black" {...props} />,
  h2: (props) => <h2 className="text-3xl font-bold tracking-tight text-black mt-10" {...props} />,
  h3: (props) => <h3 className="text-2xl font-semibold tracking-tight text-black mt-8" {...props} />,
  p: (props) => <p className="text-gray-700 leading-relaxed" {...props} />,
  a: (props) => <a className="text-[#0071e3] hover:underline" {...props} />,
  code: (props) => <code className="px-1.5 py-0.5 rounded bg-gray-100 text-gray-800" {...props} />,
  pre: (props) => (
    <pre className="rounded-2xl bg-gray-950 text-gray-100 p-6 overflow-x-auto shadow-inner" {...props} />
  ),
  blockquote: (props) => (
    <blockquote className="border-l-4 border-gray-200 pl-4 italic text-gray-600" {...props} />
  ),
  ul: (props) => <ul className="list-disc pl-6 text-gray-700" {...props} />,
  ol: (props) => <ol className="list-decimal pl-6 text-gray-700" {...props} />,
};
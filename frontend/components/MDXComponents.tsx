// frontend/components/MDXComponents.tsx
"use client";

import * as React from "react";

/**
 * Components you can pass into MDX as:
 *   <MDXContent components={MDXComponents} />
 *
 * Works with @next/mdx and most MDX pipelines.
 */
export const MDXComponents: Record<string, React.ComponentType<any>> = {
  // Typography
  h1: (props: any) => <h1 className="scroll-mt-24" {...props} />,
  h2: (props: any) => <h2 className="scroll-mt-24" {...props} />,
  h3: (props: any) => <h3 className="scroll-mt-24" {...props} />,
  h4: (props: any) => <h4 className="scroll-mt-24" {...props} />,

  a: ({ href, ...props }: any) => (
    <a
      href={href}
      {...props}
      target={href?.startsWith("#") ? undefined : "_blank"}
      rel={href?.startsWith("#") ? undefined : "noreferrer"}
      className="text-[#0071e3] no-underline hover:underline"
    />
  ),

  // Tables
  table: (props: any) => (
    <div className="my-8 w-full overflow-x-auto rounded-2xl border border-gray-100 bg-white">
      <table className="w-full border-collapse" {...props} />
    </div>
  ),
  th: (props: any) => <th className="text-left text-sm font-semibold text-gray-700 p-3 border-b border-gray-100" {...props} />,
  td: (props: any) => <td className="text-sm text-gray-600 p-3 border-b border-gray-50 align-top" {...props} />,

  // Code blocks
  pre: (props: any) => (
    <pre
      {...props}
      className="rounded-2xl border border-gray-100 bg-[#0b1020] text-gray-100 p-5 overflow-x-auto"
    />
  ),
  code: (props: any) => (
    <code
      {...props}
      className="rounded-md bg-gray-100 px-1.5 py-0.5 text-[0.95em] text-gray-800"
    />
  ),

  // Blockquote
  blockquote: (props: any) => (
    <blockquote
      {...props}
      className="border-l-4 border-gray-200 pl-4 italic text-gray-600 bg-gray-50/50 rounded-r-xl py-2"
    />
  ),

  // Horizontal rule
  hr: (props: any) => <hr className="my-10 border-gray-200" {...props} />,
};

export default MDXComponents;
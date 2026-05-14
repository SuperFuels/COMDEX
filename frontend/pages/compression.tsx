// frontend/pages/compression.tsx
"use client";

import type { NextPage } from "next";
import Shell from "../components/Shell";
import CompressionTab from "../tabs/compression";

const CompressionPage: NextPage = () => {
  return (
    <Shell activeKey="compression">
      <CompressionTab />
    </Shell>
  );
};

export default CompressionPage;
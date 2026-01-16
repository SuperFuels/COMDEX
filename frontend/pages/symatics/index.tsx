"use client";

import type { NextPage } from "next";
import Shell from "../../components/Shell";
import SymaticsTab from "../../tabs/symatics";

const SymaticsPage: NextPage = () => {
  return (
    <Shell maxWidth="max-w-[1400px]">
      <SymaticsTab />
    </Shell>
  );
};

export default SymaticsPage;
"use client";

import type { NextPage } from "next";
import Shell from "../../components/Shell";
import SymaticsTab from "../../tabs/symatics";

const SymaticsPage: NextPage = () => {
  return (
    <Shell>
      <SymaticsTab />
    </Shell>
  );
};

export default SymaticsPage;
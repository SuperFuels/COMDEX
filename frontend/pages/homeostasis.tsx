// /workspaces/COMDEX/frontend/pages/homeostasis.tsx
"use client";

import type { NextPage } from "next";
import Shell from "../components/Shell";
import HomeostasisTab from "../tabs/Aion/homeostasis";

const HomeostasisPage: NextPage = () => {
  return (
    <Shell activeKey="homeostasis">
      <HomeostasisTab />
    </Shell>
  );
};

export default HomeostasisPage;
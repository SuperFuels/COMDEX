// frontend/pages/index.tsx
"use client";

import type { NextPage } from "next";
import Shell from "../components/Shell";
import GlyphTab from "../tabs/glyph";

/**
 * "/" should look identical to the app experience:
 * same Shell, same TabDock, same content as the default tab.
 * This preserves visual + functional behavior while allowing code splitting.
 */
const Home: NextPage = () => {
  return (
    <Shell>
      <GlyphTab />
    </Shell>
  );
};

export default Home;
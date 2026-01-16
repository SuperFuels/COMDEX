// frontend/pages/index.tsx
"use client";

import { useEffect } from "react";
import type { NextPage } from "next";
import { useRouter } from "next/router";

const Home: NextPage = () => {
  const router = useRouter();

  useEffect(() => {
    router.replace("/glyph"); // ✅ choose your default landing route
  }, [router]);

  return null;
};

export default Home;
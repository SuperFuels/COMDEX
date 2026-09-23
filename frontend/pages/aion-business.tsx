"use client";

import type { NextPage } from "next";
import { useRouter } from "next/router";
import Shell from "../components/Shell";
import BoardroomPage from "../src/glyphnet/components/boardroom/BoardroomPage";
import BusinessDashboard from "../src/glyphnet/components/boardroom/BusinessDashboard";
import MarketingStreamPage from "../src/glyphnet/components/boardroom/MarketingStreamPage";
import BrandFoundationPage from "../src/glyphnet/components/boardroom/BrandFoundationPage";

type DesktopView =
  | "boardroom"
  | "dashboard"
  | "marketing_stream"
  | "brand_foundation"
  | "operations_flow";

function normalizeDesktopView(value: unknown): DesktopView {
  const raw = Array.isArray(value) ? value[0] : value;

  switch (raw) {
    case "dashboard":
      return "dashboard";
    case "marketing_stream":
      return "marketing_stream";
    case "brand_foundation":
      return "brand_foundation";
    case "operations_flow":
      return "operations_flow";
    case "boardroom":
    default:
      return "boardroom";
  }
}

const AionBusinessPage: NextPage = () => {
  const router = useRouter();
  const desktopView = normalizeDesktopView(router.query.desktopView);
  const embeddedInTessaris = router.query.embed === "tessaris";

  let content: React.ReactNode;

  switch (desktopView) {
    case "dashboard":
      content = <BusinessDashboard />;
      break;
    case "marketing_stream":
      content = <MarketingStreamPage />;
      break;
    case "brand_foundation":
      content = <BrandFoundationPage />;
      break;
    case "operations_flow":
      content = <BoardroomPage />;
      break;
    case "boardroom":
    default:
      content = <BoardroomPage />;
      break;
  }

  if (embeddedInTessaris) {
    return (
      <main
        data-aion-business-embedded-in-tessaris="true"
        style={{ width: "100vw", height: "100vh", overflow: "auto", background: "#f3f4f6" }}
      >
        {content}
      </main>
    );
  }

  return (
    <Shell activeKey="aion-business" maxWidth="max-w-[1900px]">
      {content}
    </Shell>
  );
};

export default AionBusinessPage;

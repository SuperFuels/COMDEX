// ===============================
// 📁 frontend/pages/sci/panels/register_goals.ts
// ===============================
import { registerPanel } from "@/lib/sci/panel_registry";
import SciGoalPanel from "@/components/SQS/SciGoalPanel";

registerPanel({
  id: "goals",
  title: "Goals",
  component: SciGoalPanel,
  makeDefaultProps: () => ({}),
});
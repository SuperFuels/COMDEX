import type { DashboardDepartmentKey } from "./boardroom.page.types";

export const WORKSPACE_ID = "costa-conexion";
export const MARKETING_OPERATOR_ID = "agent_marketing_operator_v1";

export const DASHBOARD_DEPARTMENT_ZONES: DashboardDepartmentKey[] = [
  "marketing",
  "sales",
  "finance",
  "operations",
  "support",
  "hr",
];

export const DASHBOARD_DEPARTMENT_CONFIG: Record<
  DashboardDepartmentKey,
  {
    operatorId: string;
    workflowId: string;
  }
> = {
  marketing: {
    operatorId: "agent_marketing_operator_v1",
    workflowId: "workflow_marketing_content_draft_v1",
  },
  sales: {
    operatorId: "operator_sales_v1",
    workflowId: "workflow_sales_v1",
  },
  finance: {
    operatorId: "operator_finance_v1",
    workflowId: "workflow_finance_v1",
  },
  operations: {
    operatorId: "operator_operations_v1",
    workflowId: "workflow_operations_v1",
  },
  support: {
    operatorId: "operator_support_v1",
    workflowId: "workflow_support_v1",
  },
  hr: {
    operatorId: "operator_hr_v1",
    workflowId: "workflow_hr_v1",
  },
};
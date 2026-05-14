export type BoardroomSeatState =
  | "healthy"
  | "warning"
  | "blocked"
  | "escalated";

export type BoardroomFlowState =
  | "normal"
  | "warning"
  | "blocked";

export type BoardroomMetric = {
  id: string;
  label: string;
  value: string;
};

export type BoardroomTaskSummary = {
  open: number;
  dueToday: number;
  blocked: number;
};

export type BoardroomSeat = {
  id: string;
  kind: "executive" | "department" | "function" | "agent";
  label: string;
  shortLabel?: string;
  owner?: string;
  state: BoardroomSeatState;
  x: number;
  y: number;
  metrics?: BoardroomMetric[];
  tasks?: BoardroomTaskSummary;
};

export type BoardroomFlow = {
  id: string;
  from: string;
  to: string;
  label?: string;
  state?: BoardroomFlowState;
};

export type BoardroomCenter = {
  revenue: string;
  cash: string;
  pipeline: string;
  profit: string;
  health: string;
};

export type BoardroomModel = {
  id: string;
  workspaceId?: string;
  label: string;
  center: BoardroomCenter;
  seats: BoardroomSeat[];
  flows: BoardroomFlow[];
};
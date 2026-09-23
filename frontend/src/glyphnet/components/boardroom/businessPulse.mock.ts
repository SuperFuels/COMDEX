import type { BusinessPulse } from "./businessPulse.types";

export const BOARDROOM_DEMO_PULSE: BusinessPulse = {
  cash: {
    onHand: 2300,
    incoming30d: 1724,
    outgoing30d: 1488,
    runwayDays: 47,
  },
  sales: {
    revenue: 22129,
    orders: 186,
    conversionRate: 3.8,
    sellThroughRate: 61,
  },
  stock: {
    units: 1573,
    value: 7196,
    daysCover: 34,
    slowStockValue: 1250,
    inTransitValue: 1075,
  },
  ops: {
    backlog: 18,
    fulfilmentRate: 94,
    blockedJobs: 3,
    avgTurnaroundDays: 2.4,
  },
  finance: {
    creditorDays: 30,
    debtorDays: 60,
    grossMarginPct: 58,
  },
  risk: {
    cash: "medium",
    stock: "medium",
    demand: "low",
    operations: "low",
  },
};
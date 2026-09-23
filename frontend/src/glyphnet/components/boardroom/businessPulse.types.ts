export type RiskLevel = "low" | "medium" | "high";

export type BusinessPulse = {
  cash: {
    onHand: number;
    incoming30d: number;
    outgoing30d: number;
    runwayDays: number;
  };
  sales: {
    revenue: number;
    orders: number;
    conversionRate: number;
    sellThroughRate: number;
  };
  stock: {
    units: number;
    value: number;
    daysCover: number;
    slowStockValue: number;
    inTransitValue: number;
  };
  ops: {
    backlog: number;
    fulfilmentRate: number;
    blockedJobs: number;
    avgTurnaroundDays: number;
  };
  finance: {
    creditorDays: number;
    debtorDays: number;
    grossMarginPct: number;
  };
  risk: {
    cash: RiskLevel;
    stock: RiskLevel;
    demand: RiskLevel;
    operations: RiskLevel;
  };
};
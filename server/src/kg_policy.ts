// server/src/kg_policy.ts
export type KG = 'personal' | 'work';

export function normalizeKg(kg: string | undefined | null): KG {
  const v = String(kg || '').toLowerCase();
  if (v === 'personal' || v === 'work') return v as KG;
  // default to personal if absent; server still logs for visibility
  return 'personal';
}

export function assertKg(kg: string): asserts kg is KG {
  const v = (kg || '').toLowerCase();
  if (v !== 'personal' && v !== 'work') {
    throw new Error(`invalid kg: ${kg}`);
  }
}

export function computeThreadId(kg: KG, topicWa?: string): string {
  const t = (topicWa && topicWa.trim()) ? topicWa : 'ucs://local/ucs_hub';
  return `kg:${kg}:${t}`;
}

export function ensureNamespaceOnEvent(base: {
  kg?: string; owner?: string; owner_wa?: string; thread_id?: string; topic_wa?: string;
}): { kg: KG; owner_wa: string; thread_id: string; topic_wa: string } {
  const kg = normalizeKg(base.kg);
  const owner_wa = (base.owner_wa || base.owner || '').trim();
  const topic_wa = (base.topic_wa || '').trim();

  if (!owner_wa) throw new Error('owner_wa is required');

  const thread_id = base.thread_id && base.thread_id.startsWith(`kg:${kg}:`)
    ? base.thread_id
    : computeThreadId(kg, topic_wa);

  return { kg, owner_wa, thread_id, topic_wa };
}
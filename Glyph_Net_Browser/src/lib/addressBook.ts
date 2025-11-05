// Simple localStorage-backed address book for UCS topics

export type AddressEntry = {
  topic: string;
  label?: string;
  uses: number;
  last: number; // epoch ms
};

const KEY = "recent_topics_v2";

function load(): AddressEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as AddressEntry[]) : [];
  } catch {
    return [];
  }
}

function save(list: AddressEntry[]) {
  localStorage.setItem(KEY, JSON.stringify(list));
}

export function rememberTopic(topic: string, label?: string) {
  const t = topic.trim();
  if (!t) return;

  const list = load();
  const i = list.findIndex((x) => x.topic === t);
  const now = Date.now();

  if (i >= 0) {
    list[i] = {
      ...list[i],
      label: label ?? list[i].label,
      uses: (list[i].uses ?? 0) + 1,
      last: now,
    };
  } else {
    list.unshift({ topic: t, label, uses: 1, last: now });
  }

  // keep most recent 20
  save(
    list
      .sort((a, b) => b.last - a.last)
      .slice(0, 20)
  );
}

export function getRecent(limit = 8): AddressEntry[] {
  return load()
    .sort((a, b) => b.last - a.last)
    .slice(0, limit);
}
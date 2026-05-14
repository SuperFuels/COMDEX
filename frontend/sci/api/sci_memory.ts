// =====================================================
//  SCI Memory API
// =====================================================
export const SCIMemoryAPI = {
  async list(userId: string) {
    const res = await fetch(`/api/sci/memory_scrolls?user_id=${encodeURIComponent(userId)}&limit=25`);
    if (!res.ok) throw new Error(`Failed to fetch scrolls (${res.status})`);
    const data = await res.json();
    return data.scrolls || [];
  },

  async replay(userId: string, label: string, containerId?: string) {
    const res = await fetch(`/api/sci/replay_scroll`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label, user_id: userId, container_id: containerId }),
    });
    const data = await res.json();
    if (!data.ok) throw new Error(data.error || "Replay failed");
    return data;
  },
};
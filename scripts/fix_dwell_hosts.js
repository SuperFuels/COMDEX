const Database = require('better-sqlite3');
const db = new Database('/workspaces/COMDEX/server/data/kg.db');

// Find dwell rows missing a real host (null, empty, or 'x.invalid')
const badRows = db.prepare(`
  SELECT id, ts, thread_id, topic_wa, payload
  FROM kg_events
  WHERE type='visit' AND kind='dwell'
    AND (
      json_extract(payload,'$.host') IS NULL
      OR json_extract(payload,'$.host')=''
      OR json_extract(payload,'$.host')='x.invalid'
    )
  ORDER BY ts ASC
`).all();

const getOriginPage = db.prepare(`
  SELECT payload FROM kg_events
  WHERE id = ? AND type='visit' AND kind='page'
  LIMIT 1
`);

const getNearestPageSameThread = db.prepare(`
  SELECT payload, ts FROM kg_events
  WHERE type='visit' AND kind='page' AND thread_id = ?
  ORDER BY ABS(ts - ?) ASC
  LIMIT 1
`);

const getNearestPageSameTopic = db.prepare(`
  SELECT payload, ts FROM kg_events
  WHERE type='visit' AND kind='page' AND topic_wa = ?
  ORDER BY ABS(ts - ?) ASC
  LIMIT 1
`);

const upd = db.prepare(`UPDATE kg_events SET payload = ? WHERE id = ?`);

function extractHostFromHref(href) {
  if (!href || typeof href !== 'string') return '';
  // Only trust absolute URLs; relative ones will produce x.invalid
  if (!/^https?:\/\//i.test(href)) return '';
  try { return (new URL(href)).host || ''; } catch { return ''; }
}

const tx = db.transaction(rows => {
  let stats = { patched: 0, fromHref: 0, fromOrigin: 0, fromThread: 0, fromTopic: 0 };

  for (const r of rows) {
    let p; try { p = JSON.parse(r.payload); } catch { p = {}; }

    // 1) Try to parse from the dwell's own href (only absolute URLs)
    let host = extractHostFromHref(p.href);
    if (host) {
      p.host = host;
      upd.run(JSON.stringify(p), r.id);
      stats.patched++; stats.fromHref++;
      continue;
    }

    // 2) If origin_id exists, copy host (and href if missing) from that PAGE
    if (p.origin_id) {
      const pg = getOriginPage.get(p.origin_id);
      if (pg?.payload) {
        try {
          const pp = JSON.parse(pg.payload);
          host = pp.host || extractHostFromHref(pp.href);
          if (!p.href && pp.href) p.href = pp.href;
        } catch {}
      }
      if (host) {
        p.host = host;
        upd.run(JSON.stringify(p), r.id);
        stats.patched++; stats.fromOrigin++;
        continue;
      }
    }

    // 3) Nearest PAGE in the same thread_id
    if (r.thread_id) {
      const nearT = getNearestPageSameThread.get(r.thread_id, r.ts);
      if (nearT?.payload) {
        try {
          const pp = JSON.parse(nearT.payload);
          host = pp.host || extractHostFromHref(pp.href);
          if (!p.href && pp.href) p.href = pp.href;
        } catch {}
      }
      if (host) {
        p.host = host;
        upd.run(JSON.stringify(p), r.id);
        stats.patched++; stats.fromThread++;
        continue;
      }
    }

    // 4) Nearest PAGE in the same topic_wa
    if (r.topic_wa) {
      const nearTopic = getNearestPageSameTopic.get(r.topic_wa, r.ts);
      if (nearTopic?.payload) {
        try {
          const pp = JSON.parse(nearTopic.payload);
          host = pp.host || extractHostFromHref(pp.href);
          if (!p.href && pp.href) p.href = pp.href;
        } catch {}
      }
      if (host) {
        p.host = host;
        upd.run(JSON.stringify(p), r.id);
        stats.patched++; stats.fromTopic++;
        continue;
      }
    }
  }
  return stats;
});

const stats = tx(badRows);
console.log('Patched:', stats);

const remaining = db.prepare(`
  SELECT COUNT(*) AS remain
  FROM kg_events
  WHERE type='visit' AND kind='dwell'
    AND (
      json_extract(payload,'$.host') IS NULL
      OR json_extract(payload,'$.host')=''
      OR json_extract(payload,'$.host')='x.invalid'
    )
`).get();
console.log('Remaining dwell with missing host:', remaining.remain);

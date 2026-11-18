(function(){
  const db = window.__db;           // { app_state: [...], app_state_history: [...] }
  window.__writes = 0;
  const norm = (iso) => iso ? iso.replace("Z", "+00:00") : iso;
  const clone = (x) => JSON.parse(JSON.stringify(x));
  let hid = 1;
  function exec(q){
    return new Promise((resolve) => setTimeout(() => {
      const fail = (window.__fail || {})[q.table + "." + q.op];
      if (fail) return resolve({ data: null, error: { code: fail === true ? "XX000" : fail, message: "falha simulada " + q.table } });
      if (!db[q.table]) return resolve({ data: null, error: { code: "PGRST205", message: "Could not find the table public." + q.table } });
      const rows = db[q.table];
      const match = rows.filter((r) => q.filters.every((f) => f(r)));
      if (q.op === "select") {
        let out = match.map(clone);
        if (q.table === "app_state_history") out.sort((a,b)=> b.created_at.localeCompare(a.created_at));
        if (q.limit) out = out.slice(0, q.limit);
        if (q.single) return resolve({ data: out[0] || null, error: null });
        return resolve({ data: out, error: null });
      }
      if (q.op === "update") {
        window.__writes++;
        match.forEach((r) => {
          if (q.table === "app_state") db.app_state_history.push({ id: hid++, user_id: r.user_id, data: clone(r.data), saved_at: r.updated_at, created_at: new Date(Date.now() - hid*60000).toISOString() });
          Object.assign(r, clone(q.payload)); if (r.updated_at) r.updated_at = norm(r.updated_at);
        });
        return resolve({ data: q.ret ? match.map((r) => ({ updated_at: r.updated_at })) : null, error: null });
      }
      if (q.op === "insert") {
        if (q.table === "app_state" && rows.some((r) => r.user_id === q.payload.user_id)) return resolve({ data: null, error: { code: "23505", message: "duplicate" } });
        window.__writes++;
        const r = clone(q.payload); if (r.updated_at) r.updated_at = norm(r.updated_at);
        if (q.table === "app_state_history") { r.id = hid++; r.created_at = new Date().toISOString(); }
        rows.push(r);
        return resolve({ data: q.ret ? [{ updated_at: r.updated_at }] : null, error: null });
      }
      if (q.op === "upsert") { window.__writes++; return resolve({ data: null, error: null }); }
    }, 30));
  }
  function from(table){
    const q = { table, op: "select", filters: [], ret: false, single: false, limit: null };
    const b = {
      select(){ if (q.op !== "select") q.ret = true; return b; },
      update(p){ q.op = "update"; q.payload = p; return b; },
      insert(p){ q.op = "insert"; q.payload = p; return b; },
      upsert(p){ q.op = "upsert"; q.payload = p; return b; },
      eq(k, v){ q.filters.push((r) => r[k] === v); return b; },
      is(k, v){ q.filters.push((r) => r[k] == v); return b; },
      order(){ return b; }, limit(n){ q.limit = n; return b; },
      maybeSingle(){ q.single = true; return b; },
      then(res, rej){ return exec(q).then(res, rej); },
    };
    return b;
  }
  const user = { id: "u1", email: "t@t" };
  window.supabase = { createClient(){ return {
    from,
    auth: { async getSession(){ return { data: { session: { user } } }; }, async signInWithPassword(){ return { data: { user }, error: null }; }, async signOut(){} },
  }; } };
})();

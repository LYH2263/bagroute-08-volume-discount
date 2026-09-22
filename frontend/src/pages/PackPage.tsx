import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = {
  id: number; name: string; max_volume_l: number;
  volume_discount_enabled: boolean; volume_discount_ratio: number;
};
type Bag = {
  id: number; bag_index: number; weight_kg: number; volume_l: number;
  volume_limit_l: number; discount_applied: boolean;
  items: { stop_name: string }[];
};
export default function PackPage() {
  const [routes, setRoutes] = useState<R[]>([]);
  const [rid, setRid] = useState<number | "">("");
  const [bags, setBags] = useState<Bag[]>([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { api<R[]>("/routes").then(r => { setRoutes(r); if (r[0]) setRid(r[0].id); }); }, []);
  const route = routes.find(r => r.id === rid);
  async function run() {
    setMsg(""); setErr("");
    try {
      const out = await api<Bag[]>("/pack", { method: "POST", body: JSON.stringify({ route_id: rid }) });
      setBags(out);
      setMsg(`完成装袋：${out.length} 袋`);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  const discounted = bags.length > 0 && bags[0].discount_applied;
  return (<>
    <h2>装袋</h2>
    <div className="toolbar">
      <select value={rid} onChange={e => setRid(Number(e.target.value))}>{routes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
      <button onClick={run}>按路线顺序双约束装袋</button>
      {route?.volume_discount_enabled && (
        <span className="badge">体积折扣 {Math.round(route.volume_discount_ratio * 100)}% · 上限 {route.max_volume_l}L → {(route.max_volume_l * route.volume_discount_ratio).toFixed(2)}L</span>
      )}
    </div>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    {bags.length > 0 && (
      <div className={discounted ? "ok" : ""}>
        本次按{discounted ? "折扣" : "原"}体积限额 {bags[0].volume_limit_l}L 装袋，重量上限不打折
      </div>
    )}
    {bags.map(b => (
      <div key={b.id}>
        <div className="mono">袋 {b.bag_index} · {b.weight_kg}kg / {b.volume_l}L（体积上限 {b.volume_limit_l}L{b.discount_applied ? " · 折扣" : ""}）</div>
        <div className="bag-row">{b.items.map((it, i) => <div className="bag-block" key={i}>{it.stop_name}</div>)}</div>
      </div>
    ))}
  </>);
}

import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = {
  id: number;
  name: string;
  max_weight_kg: number;
  max_volume_l: number;
  volume_discount_enabled: boolean;
  volume_discount_ratio: number;
  effective_max_volume_l: number;
};
type Bag = {
  id: number;
  bag_index: number;
  weight_kg: number;
  volume_l: number;
  volume_discount_applied: boolean;
  volume_limit_l: number | null;
  items: { stop_name: string }[];
};
export default function PackPage() {
  const [routes, setRoutes] = useState<R[]>([]);
  const [rid, setRid] = useState<number | "">("");
  const [bags, setBags] = useState<Bag[]>([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { api<R[]>("/routes").then(r => { setRoutes(r); if (r[0]) setRid(r[0].id); }); }, []);
  const selected = routes.find(r => r.id === rid);
  async function run() {
    setMsg(""); setErr("");
    try {
      const out = await api<Bag[]>("/pack", { method: "POST", body: JSON.stringify({ route_id: rid }) });
      setBags(out);
      const applied = out.length > 0 && out[0].volume_discount_applied;
      const limit = out.length > 0 ? out[0].volume_limit_l : null;
      if (applied && limit != null) {
        setMsg(`完成装袋：${out.length} 袋 · 本次按体积折扣限额 ${limit}L 装袋（原上限已打折）`);
      } else {
        setMsg(`完成装袋：${out.length} 袋 · 按原体积上限装袋`);
      }
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>装袋</h2>
    <div className="toolbar">
      <select value={rid} onChange={e => setRid(Number(e.target.value))}>{routes.map(r => <option key={r.id} value={r.id}>{r.name}</option>)}</select>
      <button onClick={run}>按路线顺序双约束装袋</button>
      {selected && (
        <span className={selected.volume_discount_enabled ? "discount-badge discount-badge--on" : "discount-badge"}>
          {selected.volume_discount_enabled
            ? `折扣开 · 体积上限 ${selected.max_volume_l}L→${selected.effective_max_volume_l}L（×${selected.volume_discount_ratio}）· 重量上限 ${selected.max_weight_kg}kg 不变`
            : `折扣关 · 体积上限 ${selected.max_volume_l}L · 重量上限 ${selected.max_weight_kg}kg`}
        </span>
      )}
    </div>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    {bags.map(b => (
      <div key={b.id}>
        <div className="mono">袋 {b.bag_index} · {b.weight_kg}kg / {b.volume_l}L
          {b.volume_discount_applied && b.volume_limit_l != null && (
            <span className="discount-tag">折扣限额 {b.volume_limit_l}L</span>
          )}
        </div>
        <div className="bag-row">{b.items.map((it, i) => <div className="bag-block" key={i}>{it.stop_name}</div>)}</div>
      </div>
    ))}
  </>);
}

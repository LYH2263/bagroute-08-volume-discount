import { useEffect, useState } from "react";
import { api } from "../api/client";
type R = {
  id: number; name: string; max_weight_kg: number; max_volume_l: number;
  volume_discount_enabled: boolean; volume_discount_ratio: number;
  effective_max_volume_l: number;
};
export default function RoutesPage() {
  const [rows, setRows] = useState<R[]>([]);
  const [msg, setMsg] = useState(""); const [err, setErr] = useState("");
  useEffect(() => { api<R[]>("/routes").then(setRows); }, []);
  function patch(id: number, p: Partial<R>) {
    setRows(rs => rs.map(r => (r.id === id ? { ...r, ...p } : r)));
  }
  async function save(r: R) {
    setMsg(""); setErr("");
    try {
      const out = await api<R>(`/routes/${r.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          volume_discount_enabled: r.volume_discount_enabled,
          volume_discount_ratio: r.volume_discount_ratio,
        }),
      });
      patch(r.id, out);
      setMsg(`已保存 ${out.name}：体积上限 ${out.effective_max_volume_l}L（重量上限不变）`);
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)); }
  }
  return (<>
    <h2>路线</h2>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr>
      <th>名称</th><th>重量上限 kg</th><th>体积上限 L</th><th>体积折扣</th><th>折扣比例</th><th>生效体积上限 L</th><th></th>
    </tr></thead>
    <tbody>{rows.map(r => {
      const eff = r.volume_discount_enabled ? r.max_volume_l * r.volume_discount_ratio : r.max_volume_l;
      return <tr key={r.id}>
        <td>{r.name}</td>
        <td className="mono">{r.max_weight_kg}</td>
        <td className="mono">{r.max_volume_l}</td>
        <td><label>
          <input type="checkbox" checked={r.volume_discount_enabled}
            onChange={e => patch(r.id, { volume_discount_enabled: e.target.checked })} /> 临时折扣
        </label></td>
        <td><input className="mono" type="number" min={0.05} max={1} step={0.05}
          style={{ width: "5.5rem" }} disabled={!r.volume_discount_enabled}
          value={r.volume_discount_ratio}
          onChange={e => patch(r.id, { volume_discount_ratio: Number(e.target.value) })} /></td>
        <td className="mono">{eff.toFixed(2)}</td>
        <td><button onClick={() => save(r)}>保存</button></td>
      </tr>;
    })}</tbody></table>
    <p>开启临时折扣后，装袋体积上限 = 原上限 × 折扣比例，重量上限不变；关闭后恢复原体积上限。保存后再次进入仍有效。</p>
  </>);
}

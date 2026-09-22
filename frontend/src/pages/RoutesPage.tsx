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
export default function RoutesPage() {
  const [rows, setRows] = useState<R[]>([]);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");
  const [savingId, setSavingId] = useState<number | null>(null);
  useEffect(() => { api<R[]>("/routes").then(setRows); }, []);

  function patchRow(id: number, patch: Partial<R>) {
    setRows(rs => rs.map(r => (r.id === id ? { ...r, ...patch } : r)));
  }

  async function save(r: R) {
    setMsg(""); setErr("");
    if (!(r.volume_discount_ratio > 0 && r.volume_discount_ratio <= 1)) {
      setErr("折扣比例需在 0（不含）到 1（含）之间");
      return;
    }
    setSavingId(r.id);
    try {
      const updated = await api<R>(`/routes/${r.id}/discount`, {
        method: "PATCH",
        body: JSON.stringify({
          volume_discount_enabled: r.volume_discount_enabled,
          volume_discount_ratio: r.volume_discount_ratio,
        }),
      });
      setRows(rs => rs.map(x => (x.id === r.id ? updated : x)));
      setMsg(
        r.volume_discount_enabled
          ? `已保存：${updated.name} 体积折扣开启，生效上限 ${updated.effective_max_volume_l}L`
          : `已保存：${updated.name} 折扣关闭，恢复体积上限 ${updated.max_volume_l}L`,
      );
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setSavingId(null);
    }
  }

  return (<>
    <h2>路线</h2>
    {msg && <div className="ok">{msg}</div>}
    {err && <div className="err">{err}</div>}
    <table className="table"><thead><tr>
      <th>名称</th><th>重量上限 kg</th><th>原体积上限 L</th>
      <th>体积折扣</th><th>折扣比例</th><th>生效体积上限 L</th><th></th>
    </tr></thead>
    <tbody>{rows.map(r => {
      const effective = r.max_volume_l * (r.volume_discount_enabled ? r.volume_discount_ratio : 1);
      return <tr key={r.id}>
        <td>{r.name}</td>
        <td className="mono">{r.max_weight_kg}</td>
        <td className="mono">{r.max_volume_l}</td>
        <td>
          <label className="discount-switch">
            <input
              type="checkbox"
              checked={r.volume_discount_enabled}
              onChange={e => patchRow(r.id, { volume_discount_enabled: e.target.checked })}
            />
            <span>{r.volume_discount_enabled ? "开" : "关"}</span>
          </label>
        </td>
        <td>
          <input
            type="number" min={0.01} max={1} step={0.05}
            className="mono discount-ratio"
            value={r.volume_discount_ratio}
            onChange={e => patchRow(r.id, { volume_discount_ratio: Number(e.target.value) })}
          />
        </td>
        <td className="mono">{effective.toFixed(2)}</td>
        <td><button onClick={() => save(r)} disabled={savingId === r.id}>
          {savingId === r.id ? "保存中…" : "保存"}
        </button></td>
      </tr>;
    })}</tbody></table>
  </>);
}

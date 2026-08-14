import { useEffect, useState } from "react";
import { WeightSummary, WeightDetail, getWeights, getWeightDetail } from "../api/client";

export default function ModelsPage() {
  const [weights, setWeights] = useState<WeightSummary[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [detail, setDetail] = useState<WeightDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  useEffect(() => {
    getWeights()
      .then(setWeights)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not reach the vault API."));
  }, []);

  async function toggle(w: WeightSummary) {
    if (expanded === w.name) {
      setExpanded(null);
      setDetail(null);
      return;
    }
    if (!w.inspectable) return;
    setExpanded(w.name);
    setLoadingDetail(true);
    try {
      const d = await getWeightDetail(w.name);
      setDetail(d);
    } catch {
      setDetail(null);
    } finally {
      setLoadingDetail(false);
    }
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">03 · Weights</div>
          <h1 className="page-title">Model Weight Assets</h1>
          <p className="page-desc">
            Header-only inspection of files in <code>00_raw_data/model_weights</code> — nothing is loaded into RAM.
          </p>
        </div>
      </div>

      {error && <p className="error-text">{error}</p>}

      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">Weight files</div>
          <span className="hint">{weights.length} file(s)</span>
        </div>
        {weights.length === 0 ? (
          <div className="empty-state">No weight files found yet — drop .safetensors, .pt, or .bin files into the folder.</div>
        ) : (
          weights.map((w) => (
            <div key={w.name}>
              <div
                className="row"
                style={{ cursor: w.inspectable ? "pointer" : "default" }}
                onClick={() => toggle(w)}
              >
                <span className="row-name">
                  {w.inspectable ? (expanded === w.name ? "▾ " : "▸ ") : "· "}
                  {w.name}
                </span>
                <span className="row-meta">
                  {w.size_mb} MB
                  {w.tensor_count !== null && ` · ${w.tensor_count} tensors`}
                  {!w.inspectable && (
                    <span className="badge neutral" style={{ marginLeft: 8 }}>
                      header n/a
                    </span>
                  )}
                </span>
              </div>
              {expanded === w.name && (
                <div style={{ padding: "0 20px 16px 32px", background: "var(--panel-alt)" }}>
                  {loadingDetail && <div className="hint">Loading header…</div>}
                  {detail && detail.name === w.name && (
                    <>
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", margin: "10px 0" }}>
                        {Object.entries(detail.dtype_breakdown ?? {}).map(([dtype, count]) => (
                          <span className="badge success" key={dtype}>
                            {dtype} × {count}
                          </span>
                        ))}
                      </div>
                      <div style={{ maxHeight: 260, overflowY: "auto" }}>
                        {detail.tensors.map((t) => (
                          <div className="row" key={t.name} style={{ padding: "6px 0" }}>
                            <span className="row-name">{t.name}</span>
                            <span className="row-meta">
                              {t.dtype} · [{t.shape.join(", ")}]
                            </span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}

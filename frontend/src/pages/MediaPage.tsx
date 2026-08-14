import { useEffect, useRef, useState } from "react";
import {
  RawVideo,
  Proxy,
  TranscodeJob,
  getRawVideos,
  getProxies,
  startTranscode,
  getJobStatus,
} from "../api/client";
import ProgressBar from "../components/ProgressBar";

export default function MediaPage() {
  const [raw, setRaw] = useState<RawVideo[]>([]);
  const [proxies, setProxies] = useState<Proxy[]>([]);
  const [job, setJob] = useState<TranscodeJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  async function load() {
    try {
      const [r, p] = await Promise.all([getRawVideos(), getProxies()]);
      setRaw(r);
      setProxies(p);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the vault API.");
    }
  }

  useEffect(() => {
    load();
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  async function handleStart() {
    const { job_id } = await startTranscode();
    pollRef.current = window.setInterval(async () => {
      const status = await getJobStatus(job_id);
      setJob(status);
      if (status.status !== "running") {
        if (pollRef.current) window.clearInterval(pollRef.current);
        load();
      }
    }, 800);
  }

  const pendingCount = raw.filter((r) => !r.proxy_exists).length;

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">02 · Media</div>
          <h1 className="page-title">Proxy Pipeline</h1>
          <p className="page-desc">
            Generates 720p proxies for raw footage in <code>00_raw_data/video_footage</code>.
          </p>
        </div>
        <button className="btn" onClick={handleStart} disabled={job?.status === "running" || pendingCount === 0}>
          {job?.status === "running" ? "Transcoding…" : `Generate proxies (${pendingCount})`}
        </button>
      </div>

      {error && <p className="error-text">{error}</p>}

      {job && (
        <div className="panel" style={{ marginBottom: 20 }}>
          <div className="panel-header">
            <div className="panel-title">
              {job.status === "running" && `Transcoding ${job.current_item ?? "…"}`}
              {job.status === "done" &&
                `Done — ${job.result?.processed ?? 0}/${job.result?.total ?? 0} proxies generated`}
              {job.status === "error" && `Job failed: ${job.error}`}
            </div>
            <span className="hint">
              {job.progress}/{job.total}
            </span>
          </div>
          <div style={{ padding: "16px 20px" }}>
            <ProgressBar percent={job.total ? (job.progress / job.total) * 100 : 0} />
            {job.result && job.result.failures.length > 0 && (
              <p className="error-text" style={{ marginTop: 10 }}>
                Failed: {job.result.failures.join(", ")}
              </p>
            )}
          </div>
        </div>
      )}

      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="panel-header">
          <div className="panel-title">Raw captures</div>
          <span className="hint">{raw.length} file(s)</span>
        </div>
        {raw.length === 0 ? (
          <div className="empty-state">No raw footage found yet — drop files into 00_raw_data/video_footage.</div>
        ) : (
          raw.map((v) => (
            <div className="row" key={v.name}>
              <span className="row-name">{v.name}</span>
              <span className="row-meta">
                {v.size_mb} MB &nbsp;
                <span className={`badge ${v.proxy_exists ? "success" : "neutral"}`}>
                  {v.proxy_exists ? "proxy ready" : "pending"}
                </span>
              </span>
            </div>
          ))
        )}
      </div>

      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">720p proxies</div>
          <span className="hint">{proxies.length} file(s)</span>
        </div>
        {proxies.length === 0 ? (
          <div className="empty-state">No proxies generated yet.</div>
        ) : (
          proxies.map((p) => (
            <div className="row" key={p.name}>
              <span className="row-name">{p.name}</span>
              <span className="row-meta">{p.size_mb} MB</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

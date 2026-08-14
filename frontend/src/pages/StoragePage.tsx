import { useEffect, useState } from "react";
import {
  DiskUsage,
  ZoneSize,
  TreeNode,
  getDiskUsage,
  getZoneSizes,
  getDirTree,
  cleanupScratch,
} from "../api/client";
import VaultDial from "../components/VaultDial";
import DirTree from "../components/DirTree";

export default function StoragePage() {
  const [disk, setDisk] = useState<DiskUsage | null>(null);
  const [zones, setZones] = useState<ZoneSize[]>([]);
  const [tree, setTree] = useState<TreeNode | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cleaning, setCleaning] = useState(false);
  const [cleanupMsg, setCleanupMsg] = useState<string | null>(null);

  async function load() {
    try {
      const [d, z, t] = await Promise.all([getDiskUsage(), getZoneSizes(), getDirTree(".", 2)]);
      setDisk(d);
      setZones(z);
      setTree(t);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not reach the vault API.");
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCleanup() {
    setCleaning(true);
    setCleanupMsg(null);
    try {
      const res = await cleanupScratch();
      setCleanupMsg(
        res.cleared_count > 0
          ? `Cleared ${res.cleared_count} file(s), freed ${(res.freed_bytes / (1024 * 1024)).toFixed(1)} MB.`
          : "Scratch directory was already clean."
      );
      await load();
    } catch (e) {
      setCleanupMsg(e instanceof Error ? e.message : "Cleanup failed.");
    } finally {
      setCleaning(false);
    }
  }

  if (error) {
    return (
      <div>
        <div className="page-eyebrow">01 · Storage</div>
        <h1 className="page-title">Vault Overview</h1>
        <p className="error-text" style={{ marginTop: 16 }}>
          {error} — is the API running? (<code>uvicorn api.main:app --reload</code> from the ASTRO root)
        </p>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-eyebrow">01 · Storage</div>
          <h1 className="page-title">Vault Overview</h1>
          <p className="page-desc">Disk headroom and zone sizes across the four vault directories.</p>
        </div>
        {disk && (
          <VaultDial
            percent={disk.percent_used}
            label={`${disk.percent_used}%`}
            caption={`${disk.free_gb} GB free`}
            danger={disk.low_space_warning}
          />
        )}
      </div>

      <div className="grid">
        {zones.map((z) => (
          <div className="card" key={z.zone}>
            <div className="stat-label">{z.zone}</div>
            <div className="stat-value">{z.size_gb} GB</div>
            <div className="stat-sub">
              {z.exists ? `${z.file_count} file(s) · ${z.path}` : `not created yet · ${z.path}`}
            </div>
          </div>
        ))}
      </div>

      <div className="panel" style={{ marginBottom: 20 }}>
        <div className="panel-header">
          <div className="panel-title">02_build_cache / temp_scratch</div>
          <button className="btn btn-ghost" onClick={handleCleanup} disabled={cleaning}>
            {cleaning ? "Clearing…" : "Clear scratch"}
          </button>
        </div>
        {cleanupMsg && (
          <div className="row">
            <span className="row-name">{cleanupMsg}</span>
          </div>
        )}
      </div>

      <div className="panel">
        <div className="panel-header">
          <div className="panel-title">Folder tree</div>
          <span className="hint">depth 2</span>
        </div>
        <div style={{ padding: "16px 20px" }}>
          {tree ? <DirTree node={tree} /> : <div className="empty-state">Loading…</div>}
        </div>
      </div>
    </div>
  );
}

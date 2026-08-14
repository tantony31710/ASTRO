import { TreeNode } from "../api/client";

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`;
}

export default function DirTree({ node }: { node: TreeNode }) {
  return (
    <div className="tree-node">
      <div className={`tree-row ${node.type}`}>
        <span>{node.type === "folder" ? "▸ " : "· "}{node.name}</span>
        <span>{formatBytes(node.size_bytes)}</span>
      </div>
      {node.children && node.children.length > 0 && (
        <div className="tree-children">
          {node.children.map((child, i) => (
            <DirTree key={`${child.name}-${i}`} node={child} />
          ))}
        </div>
      )}
    </div>
  );
}

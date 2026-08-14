interface VaultDialProps {
  percent: number; // 0-100
  size?: number;
  label: string;
  caption: string;
  danger?: boolean;
}

export default function VaultDial({ percent, size = 120, label, caption, danger }: VaultDialProps) {
  const stroke = 8;
  const radius = (size - stroke) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.min(100, Math.max(0, percent));
  const offset = circumference - (clamped / 100) * circumference;
  const tickCount = 24;

  return (
    <div className="vault-dial" style={{ width: size, height: size }}>
      <svg width={size} height={size}>
        {/* tick marks, like a combination dial */}
        {Array.from({ length: tickCount }).map((_, i) => {
          const angle = (i / tickCount) * 2 * Math.PI;
          const inner = radius + stroke / 2 + 2;
          const outer = inner + (i % 3 === 0 ? 6 : 3);
          const cx = size / 2;
          const cy = size / 2;
          const x1 = cx + inner * Math.cos(angle);
          const y1 = cy + inner * Math.sin(angle);
          const x2 = cx + outer * Math.cos(angle);
          const y2 = cy + outer * Math.sin(angle);
          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="var(--border)"
              strokeWidth={1}
              transform={`rotate(90 ${cx} ${cy})`}
            />
          );
        })}
        <circle
          className="vault-dial-track"
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
        />
        <circle
          className={`vault-dial-fill${danger ? " danger" : ""}`}
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={stroke}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className="vault-dial-label">
        <div className="vault-dial-value">{label}</div>
        <div className="vault-dial-caption">{caption}</div>
      </div>
    </div>
  );
}

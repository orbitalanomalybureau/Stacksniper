export function SkeletonRow({ cols = 5 }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="py-3 px-3">
          <div className={`skeleton-text ${i === 0 ? "w-24" : "w-16"}`} />
        </td>
      ))}
    </tr>
  );
}

export function SkeletonCard() {
  return (
    <div className="card space-y-3 animate-pulse">
      <div className="skeleton h-5 w-1/3" />
      <div className="skeleton h-8 w-1/2" />
      <div className="skeleton-text" />
    </div>
  );
}

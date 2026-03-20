import React from 'react';

export function SkeletonLine({ width = '100%', height = '14px', className = '' }) {
  return (
    <div
      className={`bg-surface2 rounded-md animate-shimmer ${className}`}
      style={{
        width,
        height,
        backgroundImage: 'linear-gradient(90deg, var(--tw-gradient-stops, rgb(var(--surface2)) 25%, rgb(var(--surface)) 50%, rgb(var(--surface2)) 75%))',
        backgroundSize: '200% 100%',
      }}
    />
  );
}

export function SkeletonCard({ lines = 3 }) {
  return (
    <div className="bg-surface border border-border rounded-[10px] p-4">
      <SkeletonLine width="40%" height="16px" className="mb-3" />
      {Array.from({ length: lines }).map((_, i) => (
        <SkeletonLine key={i} width={`${70 + Math.random() * 30}%`} className="mb-2" />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 8, cols = 6 }) {
  return (
    <div className="overflow-x-auto">
      <div className="grid gap-1.5">
        <div className="flex gap-2 py-2">
          {Array.from({ length: cols }).map((_, i) => (
            <SkeletonLine key={i} width={i === 1 ? '140px' : '70px'} height="12px" />
          ))}
        </div>
        {Array.from({ length: rows }).map((_, ri) => (
          <div key={ri} className="flex gap-2 py-1.5">
            {Array.from({ length: cols }).map((_, ci) => (
              <SkeletonLine key={ci} width={ci === 1 ? '140px' : '70px'} height="14px" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function LoadingSkeleton({ type = 'card' }) {
  if (type === 'table') return <SkeletonTable />;
  return (
    <div className="grid gap-3">
      <SkeletonCard lines={4} />
      <SkeletonCard lines={3} />
      <SkeletonCard lines={2} />
    </div>
  );
}

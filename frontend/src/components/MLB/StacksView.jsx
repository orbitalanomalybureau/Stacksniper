import React from 'react';

export default function StacksView({ stacks }) {
  if (!stacks || stacks.length === 0) {
    return (
      <div className="py-20 text-center text-venom">
        Generate lineups to see stack recommendations
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-text-muted text-[10px] font-semibold tracking-[2px] uppercase mb-3">
        TOP STACKS
      </h3>
      <div className="grid gap-2.5">
        {stacks.map((stack, idx) => (
          <div
            key={idx}
            className={`bg-surface rounded-lg p-5 border border-border ${
              idx < 3 ? 'border-l-[3px] border-l-venom' : ''
            }`}
          >
            <div className="flex justify-between items-center mb-2.5">
              <div className="flex items-center gap-2.5">
                <span
                  className={`rounded-full w-6 h-6 flex items-center justify-center text-[11px] font-bold ${
                    idx < 3
                      ? 'bg-venom text-primary'
                      : 'bg-surface2 text-text-muted'
                  }`}
                >
                  {idx + 1}
                </span>
                <div>
                  <span className="text-text-primary font-bold text-[15px]">
                    {stack.team}
                  </span>
                  <span className="text-text-muted text-[11px] ml-2">
                    vs {stack.opponent}
                  </span>
                </div>
              </div>
              <div className="flex gap-4 items-center">
                <div className="text-right">
                  <div className="text-venom font-bold text-sm">
                    {stack.total_points?.toFixed(1)} pts
                  </div>
                  <div className="text-text-muted text-[10px]">
                    ${stack.total_salary?.toLocaleString()}
                  </div>
                </div>
                <div
                  className={`rounded-md px-2 py-1 text-center border ${
                    stack.stack_quality > 0.7
                      ? 'bg-green-950/50 border-venom'
                      : stack.stack_quality > 0.4
                        ? 'bg-yellow-950/50 border-yellow-500'
                        : 'bg-red-950/50 border-red-500'
                  }`}
                >
                  <div className="text-text-muted text-[8px] uppercase">
                    Quality
                  </div>
                  <div
                    className={`text-[13px] font-bold ${
                      stack.stack_quality > 0.7
                        ? 'text-venom'
                        : stack.stack_quality > 0.4
                          ? 'text-yellow-500'
                          : 'text-red-500'
                    }`}
                  >
                    {(stack.stack_quality * 100).toFixed(0)}
                  </div>
                </div>
              </div>
            </div>

            <div className="flex gap-1.5 flex-wrap">
              {stack.players?.map((p, pi) => (
                <div
                  key={pi}
                  className="bg-surface2 rounded-md px-2.5 py-1.5 border border-border/50"
                >
                  <div className="text-text-primary text-xs font-semibold">
                    {p.name}
                  </div>
                  <div className="flex gap-2 mt-0.5">
                    <span className="text-blue-400 text-[10px]">
                      {p.position}
                    </span>
                    <span className="text-venom text-[10px]">
                      {p.dk_pts?.toFixed(1)}
                    </span>
                    <span className="text-text-muted text-[10px]">
                      ${p.salary?.toLocaleString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-2 flex gap-4">
              <span className="text-text-muted text-[10px]">
                {stack.size}-man stack
              </span>
              <span className="text-text-muted text-[10px]">
                Avg: {stack.avg_points?.toFixed(1)} pts/player
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

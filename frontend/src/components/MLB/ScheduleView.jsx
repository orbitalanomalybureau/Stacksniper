import React from 'react';

export default function ScheduleView({ schedule, simDate }) {
  return (
    <div>
      <h3 className="text-sm font-bold tracking-widest text-text-muted uppercase mb-4 font-mono">
        MLB SCHEDULE &mdash; {simDate}
      </h3>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse font-mono text-xs">
          <thead>
            <tr>
              <th className="text-left px-4 py-3 text-[10px] font-bold tracking-widest text-text-muted uppercase border-b border-border/50">Away</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold tracking-widest text-text-muted uppercase border-b border-border/50">Home</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold tracking-widest text-text-muted uppercase border-b border-border/50">Away SP</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold tracking-widest text-text-muted uppercase border-b border-border/50">Home SP</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold tracking-widest text-text-muted uppercase border-b border-border/50">Venue</th>
              <th className="text-left px-4 py-3 text-[10px] font-bold tracking-widest text-text-muted uppercase border-b border-border/50">Status</th>
            </tr>
          </thead>
          <tbody>
            {schedule.map((g, i) => (
              <tr key={i} className={i % 2 ? 'bg-surface2/50' : 'bg-transparent'}>
                <td className="px-4 py-3 text-text-primary border-b border-border/30"><strong>{g.away_team?.abbr}</strong></td>
                <td className="px-4 py-3 text-text-primary border-b border-border/30"><strong>{g.home_team?.abbr}</strong></td>
                <td className="px-4 py-3 text-text-primary border-b border-border/30">{g.away_team?.probable_pitcher?.name || 'TBD'}</td>
                <td className="px-4 py-3 text-text-primary border-b border-border/30">{g.home_team?.probable_pitcher?.name || 'TBD'}</td>
                <td className="px-4 py-3 text-text-primary border-b border-border/30">{g.venue?.name}</td>
                <td className="px-4 py-3 text-text-primary border-b border-border/30">
                  <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                    g.status === 'Final'
                      ? 'bg-[#003300] text-venom'
                      : 'bg-[#332200] text-[#ffaa00]'
                  }`}>
                    {g.status}
                  </span>
                </td>
              </tr>
            ))}
            {schedule.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-text-muted border-b border-border/30">
                  No games scheduled for this date
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

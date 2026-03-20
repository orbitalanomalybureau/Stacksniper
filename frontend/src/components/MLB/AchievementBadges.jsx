import React, { useState, useRef, useEffect } from 'react';

function Tooltip({ text, children }) {
  const [show, setShow] = useState(false);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const ref = useRef(null);

  const handleEnter = () => {
    if (ref.current) {
      const rect = ref.current.getBoundingClientRect();
      setPos({ x: rect.left + rect.width / 2, y: rect.top });
    }
    setShow(true);
  };

  return (
    <span
      ref={ref}
      onMouseEnter={handleEnter}
      onMouseLeave={() => setShow(false)}
      className="relative inline-flex"
    >
      {children}
      {show && (
        <span
          className="fixed bg-surface2 border border-border rounded-md px-2.5 py-1.5 text-[11px] text-text-primary whitespace-nowrap z-[9999] pointer-events-none shadow-lg"
          style={{
            left: pos.x,
            top: pos.y - 8,
            transform: 'translate(-50%, -100%)',
          }}
        >
          {text}
        </span>
      )}
    </span>
  );
}

function BadgeIcon({ achievement, onClick, compact }) {
  const { icon, name, description, unlocked } = achievement;
  const [hovered, setHovered] = useState(false);

  const badge = (
    <div
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`w-[34px] h-[34px] flex items-center justify-center rounded-lg cursor-pointer text-lg transition-all duration-200 ${
        unlocked
          ? 'bg-surface border border-border'
          : 'bg-surface2 border border-border/30'
      } ${hovered && unlocked ? 'scale-110 shadow-[0_0_12px_rgba(57,255,20,0.13)]' : 'scale-100'}`}
      style={{
        filter: unlocked ? 'none' : 'grayscale(100%) brightness(0.4)',
      }}
    >
      {icon}
    </div>
  );

  const tooltipText = unlocked ? `${name} — ${description}` : `Locked: ${description}`;

  return (
    <Tooltip text={tooltipText}>
      {badge}
    </Tooltip>
  );
}

function AchievementCard({ achievement }) {
  const { icon, name, description, unlocked } = achievement;

  return (
    <div className={`flex items-center gap-3.5 px-4 py-3.5 rounded-lg border transition-all duration-200 ${
      unlocked
        ? 'bg-surface border-border opacity-100'
        : 'bg-surface2 border-border/30 opacity-50'
    }`}>
      <div className="text-[28px] flex-shrink-0"
        style={{ filter: unlocked ? 'none' : 'grayscale(100%) brightness(0.4)' }}>
        {icon}
      </div>
      <div className="flex-1">
        <div className={`text-[13px] font-bold mb-0.5 ${
          unlocked ? 'text-text-primary' : 'text-text-muted/40'
        }`}>
          {name}
        </div>
        <div className={`text-[11px] ${
          unlocked ? 'text-text-muted' : 'text-text-muted/40'
        }`}>
          {description}
        </div>
      </div>
      {unlocked && (
        <div className="text-[10px] text-venom font-bold tracking-wider uppercase">
          UNLOCKED
        </div>
      )}
    </div>
  );
}

export default function AchievementBadges({ achievements }) {
  const [expanded, setExpanded] = useState(false);
  const panelRef = useRef(null);

  const items = achievements || [];
  const unlockedCount = items.filter(a => a.unlocked).length;
  const totalCount = items.length;

  // Close panel on outside click
  useEffect(() => {
    if (!expanded) return;
    const handler = (e) => {
      if (panelRef.current && !panelRef.current.contains(e.target)) {
        setExpanded(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [expanded]);

  if (items.length === 0) return null;

  return (
    <div className="relative inline-flex items-center gap-1.5" ref={panelRef}>
      {/* Compact mode: icon row */}
      <div className="flex gap-1 items-center">
        {items.map(a => (
          <BadgeIcon
            key={a.key}
            achievement={a}
            compact
            onClick={() => setExpanded(!expanded)}
          />
        ))}
      </div>

      {/* Counter label */}
      <div
        onClick={() => setExpanded(!expanded)}
        className="text-[10px] text-venom font-bold tracking-wider cursor-pointer ml-1 whitespace-nowrap"
      >
        {unlockedCount}/{totalCount}
      </div>

      {/* Expanded panel */}
      {expanded && (
        <div className="absolute top-[calc(100%+8px)] right-0 w-[340px] max-h-[420px] overflow-y-auto bg-primary border border-border rounded-xl p-4 z-[1000] shadow-2xl">
          <div className="flex justify-between items-center mb-3.5">
            <div className="text-[13px] font-bold text-venom tracking-wider">
              ACHIEVEMENTS
            </div>
            <div className="text-[11px] text-text-muted">
              {unlockedCount} of {totalCount} unlocked
            </div>
          </div>

          {/* Progress bar */}
          <div className="h-1 bg-surface2 rounded-sm mb-3.5 overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-venom to-venom-glow rounded-sm transition-all duration-400"
              style={{ width: totalCount > 0 ? `${(unlockedCount / totalCount) * 100}%` : '0%' }}
            />
          </div>

          <div className="flex flex-col gap-2">
            {/* Unlocked first, then locked */}
            {[...items].sort((a, b) => (b.unlocked ? 1 : 0) - (a.unlocked ? 1 : 0)).map(a => (
              <AchievementCard key={a.key} achievement={a} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

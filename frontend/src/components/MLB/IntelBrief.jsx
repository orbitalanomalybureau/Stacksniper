import React, { useState } from 'react';

const SECTION_ICONS = {
  weather: '\u2601\uFE0F',
  injuries: '\uD83E\uDE79',
  pitching: '\u26BE',
  lineups: '\uD83D\uDCCB',
  trends: '\uD83D\uDCC8',
  picks: '\uD83C\uDFAF',
  stacks: '\uD83D\uDD25',
  vegas: '\uD83C\uDFB0',
  default: '\uD83D\uDCA1',
};

export default function IntelBrief({ brief, onGenerate, loading }) {
  const [expandedSection, setExpandedSection] = useState(null);

  if (!brief && !loading) {
    return (
      <div className="py-16 px-10 text-center">
        <div className="text-[40px] mb-4">{'\uD83E\uDDE0'}</div>
        <div className="text-venom text-base mb-2">
          AI Intelligence Brief
        </div>
        <div className="text-text-muted text-xs mb-5">
          Generate an LLM-powered analysis of today&apos;s slate
        </div>
        <button
          onClick={onGenerate}
          className="px-6 py-2.5 rounded-md font-mono text-xs font-semibold tracking-wider transition-all cursor-pointer bg-gradient-to-br from-venom to-venom-glow text-primary"
        >
          Generate Brief
        </button>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="py-20 px-10 text-center">
        <div className="text-venom text-sm mb-2">
          {'\uD83E\uDDE0'} Generating intelligence brief...
        </div>
        <div className="text-text-muted text-[11px]">
          Analyzing slate, injuries, weather, and trends
        </div>
      </div>
    );
  }

  const sections = brief?.sections || [];
  const summary = brief?.summary || '';
  const provider = brief?.provider || '';

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-venom text-xs font-semibold tracking-widest uppercase m-0">
          {'\uD83E\uDDE0'} INTELLIGENCE BRIEF
        </h3>
        <div className="flex gap-2 items-center">
          {provider && (
            <span className="text-text-muted text-[10px]">
              via {provider}
            </span>
          )}
          <button
            onClick={onGenerate}
            className="px-4 py-1.5 rounded-md font-mono text-[10px] font-semibold tracking-wider transition-all cursor-pointer bg-surface2 text-text-muted border border-border/50 hover:border-venom/50 hover:text-text-primary"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Summary */}
      {summary && (
        <div className="bg-surface rounded-lg p-5 border border-border mb-4 border-l-[3px] border-l-venom">
          <div className="text-text-muted text-[10px] uppercase mb-1.5">
            Summary
          </div>
          <div className="text-text-secondary text-[13px] leading-[1.6]">
            {summary}
          </div>
        </div>
      )}

      {/* Section Cards */}
      <div className="grid gap-2.5">
        {sections.map((section, idx) => {
          const icon = SECTION_ICONS[section.type?.toLowerCase()] || SECTION_ICONS.default;
          const isExpanded = expandedSection === idx;
          return (
            <div
              key={idx}
              className={`bg-surface rounded-lg p-5 cursor-pointer transition-colors ${
                isExpanded ? 'border border-venom' : 'border border-border'
              }`}
              onClick={() => setExpandedSection(isExpanded ? null : idx)}
            >
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-2.5">
                  <span className="text-lg">{icon}</span>
                  <span className="text-white font-semibold text-[13px]">
                    {section.title || section.type}
                  </span>
                </div>
                <span
                  className="text-text-muted text-[11px] transition-transform duration-200"
                  style={{ transform: isExpanded ? 'rotate(180deg)' : 'none' }}
                >
                  &#9660;
                </span>
              </div>
              {isExpanded && section.content && (
                <div className="mt-3 pt-3 border-t border-border/50 text-text-secondary text-xs leading-[1.7] whitespace-pre-wrap">
                  {section.content}
                </div>
              )}
              {isExpanded && section.items && (
                <div className="mt-3 pt-3 border-t border-border/50">
                  {section.items.map((item, ii) => (
                    <div
                      key={ii}
                      className={`py-1.5 text-text-secondary text-xs leading-[1.5] ${
                        ii < section.items.length - 1 ? 'border-b border-border/50' : ''
                      }`}
                    >
                      {typeof item === 'string' ? item : (
                        <div>
                          <span className="text-white font-semibold">
                            {item.player || item.team || item.game}
                          </span>
                          {item.team && item.player && (
                            <span className="text-venom ml-1.5 text-[11px]">
                              ({item.team})
                            </span>
                          )}
                          {(item.reason || item.note || item.dfs_impact || item.impact || item.implication || item.condition || item.movement || item.salary_range || item.status) && (
                            <div className="text-text-muted mt-0.5 text-[11px]">
                              {item.salary_range && <span className="text-venom mr-1.5">{item.salary_range}</span>}
                              {item.status && <span className="text-amber-400 mr-1.5">{item.status}</span>}
                              {item.condition && <span className="text-blue-400 mr-1.5">{item.condition}</span>}
                              {item.movement && <span className="text-venom mr-1.5">{item.movement}</span>}
                              {item.reason || item.note || item.dfs_impact || item.impact || item.implication}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

import React, { useState, useCallback } from 'react';
import { DndContext, closestCenter, useSensor, useSensors, PointerSensor } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy, useSortable, arrayMove } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

const ROSTER_SLOTS = ['P', 'P', 'C', '1B', '2B', '3B', 'SS', 'OF', 'OF', 'OF'];

function SortablePlayer({ player, slot, index }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: `slot-${index}`,
  });

  return (
    <div
      ref={setNodeRef}
      className={`px-3.5 py-2.5 bg-surface rounded-lg mb-1.5 flex justify-between items-center cursor-grab text-xs transition-all ${
        isDragging ? 'border border-venom opacity-50' : 'border border-border'
      }`}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
      }}
      {...attributes}
      {...listeners}
    >
      <div className="flex gap-2.5 items-center">
        <span className="text-venom font-bold w-7 text-[10px] uppercase">
          {slot}
        </span>
        <span className="text-white font-medium">
          {player?.name || '— Empty —'}
        </span>
        {player?.team && (
          <span className="text-text-muted text-[10px]">{player.team}</span>
        )}
      </div>
      {player && (
        <div className="flex gap-3.5 text-[11px]">
          <span className="text-venom">{player.dk_points?.toFixed(1)} pts</span>
          <span className="text-text-muted">${player.salary?.toLocaleString()}</span>
        </div>
      )}
    </div>
  );
}

export default function LineupBuilder({ lineup, allPlayers, onSave, onReset }) {
  const [players, setPlayers] = useState(() =>
    lineup?.players ? [...lineup.players] : Array(10).fill(null)
  );
  const [history, setHistory] = useState([]);
  const [redoStack, setRedoStack] = useState([]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const totalSalary = players.reduce((sum, p) => sum + (p?.salary || 0), 0);
  const totalPoints = players.reduce((sum, p) => sum + (p?.dk_points || 0), 0);
  const salaryRemaining = 50000 - totalSalary;

  const pushHistory = useCallback(() => {
    setHistory(prev => [...prev, players.map(p => p ? { ...p } : null)]);
    setRedoStack([]);
  }, [players]);

  const undo = useCallback(() => {
    if (history.length === 0) return;
    setRedoStack(prev => [...prev, players.map(p => p ? { ...p } : null)]);
    setPlayers(history[history.length - 1]);
    setHistory(prev => prev.slice(0, -1));
  }, [history, players]);

  const redo = useCallback(() => {
    if (redoStack.length === 0) return;
    setHistory(prev => [...prev, players.map(p => p ? { ...p } : null)]);
    setPlayers(redoStack[redoStack.length - 1]);
    setRedoStack(prev => prev.slice(0, -1));
  }, [redoStack, players]);

  // Keyboard shortcuts
  React.useEffect(() => {
    const handler = (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      }
      if ((e.metaKey || e.ctrlKey) && e.key === 'z' && e.shiftKey) {
        e.preventDefault();
        redo();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [undo, redo]);

  const handleDragEnd = (event) => {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    pushHistory();
    const oldIndex = parseInt(active.id.replace('slot-', ''));
    const newIndex = parseInt(over.id.replace('slot-', ''));
    setPlayers(prev => arrayMove(prev, oldIndex, newIndex));
  };

  const swapPlayer = (slotIndex, newPlayer) => {
    pushHistory();
    setPlayers(prev => {
      const next = [...prev];
      next[slotIndex] = newPlayer;
      return next;
    });
  };

  const handleReset = () => {
    pushHistory();
    if (lineup?.players) {
      setPlayers([...lineup.players]);
    }
    if (onReset) onReset();
  };

  return (
    <div className="py-5">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-venom m-0 text-base font-bold">
          Lineup Builder
        </h3>
        <div className="flex gap-2">
          <button
            onClick={undo}
            disabled={history.length === 0}
            className={`px-3 py-1.5 rounded-md border border-border bg-transparent text-[11px] font-inherit ${
              history.length ? 'text-text-primary cursor-pointer hover:border-venom/50' : 'text-text-muted cursor-default'
            } transition-colors`}
          >
            ↩ Undo
          </button>
          <button
            onClick={redo}
            disabled={redoStack.length === 0}
            className={`px-3 py-1.5 rounded-md border border-border bg-transparent text-[11px] font-inherit ${
              redoStack.length ? 'text-text-primary cursor-pointer hover:border-venom/50' : 'text-text-muted cursor-default'
            } transition-colors`}
          >
            Redo ↪
          </button>
          <button
            onClick={handleReset}
            className="px-3 py-1.5 rounded-md border border-border bg-transparent text-text-primary cursor-pointer text-[11px] font-inherit hover:border-venom/50 transition-colors"
          >
            Reset to Optimizer
          </button>
          {onSave && (
            <button
              onClick={() => onSave(players)}
              className="px-3 py-1.5 rounded-md border-none bg-venom text-black font-bold cursor-pointer text-[11px] font-inherit hover:opacity-90 transition-opacity"
            >
              Save Lineup
            </button>
          )}
        </div>
      </div>

      {/* Salary Summary */}
      <div className="flex gap-5 mb-4 px-4 py-3 bg-surface rounded-lg border border-border text-xs">
        <div>
          <span className="text-text-muted">Salary: </span>
          <span className={`font-bold ${totalSalary > 50000 ? 'text-red-400' : 'text-venom'}`}>
            ${totalSalary.toLocaleString()}
          </span>
          <span className="text-text-muted"> / $50,000</span>
        </div>
        <div>
          <span className="text-text-muted">Remaining: </span>
          <span className={`font-semibold ${salaryRemaining < 0 ? 'text-red-400' : 'text-text-primary'}`}>
            ${salaryRemaining.toLocaleString()}
          </span>
        </div>
        <div>
          <span className="text-text-muted">Projected: </span>
          <span className="text-venom font-bold">{totalPoints.toFixed(1)} pts</span>
        </div>
      </div>

      {/* Draggable Roster */}
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
        <SortableContext items={ROSTER_SLOTS.map((_, i) => `slot-${i}`)} strategy={verticalListSortingStrategy}>
          {ROSTER_SLOTS.map((slot, i) => (
            <SortablePlayer key={`slot-${i}`} player={players[i]} slot={slot} index={i} />
          ))}
        </SortableContext>
      </DndContext>

      {/* Available Players */}
      {allPlayers && allPlayers.length > 0 && (
        <div className="mt-5">
          <div className="text-text-muted text-[11px] font-semibold mb-2 tracking-wider">
            AVAILABLE PLAYERS (click to swap)
          </div>
          <div className="max-h-[300px] overflow-y-auto">
            {allPlayers.slice(0, 50).map((p, i) => {
              const isInLineup = players.some(lp => lp && lp.player_id === p.player_id);
              if (isInLineup) return null;
              return (
                <div
                  key={i}
                  className="px-3 py-1.5 text-[11px] flex justify-between items-center border-b border-border cursor-pointer opacity-80 hover:opacity-100 hover:bg-surface/50 transition-all"
                  onClick={() => {
                    const slotIdx = ROSTER_SLOTS.findIndex((slot, idx) => {
                      if (players[idx]) return false;
                      return true;
                    });
                    if (slotIdx >= 0) swapPlayer(slotIdx, p);
                  }}
                >
                  <div className="flex gap-2">
                    <span className="text-venom w-6">{p.position}</span>
                    <span className="text-text-primary">{p.name}</span>
                    <span className="text-text-muted">{p.team}</span>
                  </div>
                  <div className="flex gap-3">
                    <span className="text-venom">{p.dk_points?.toFixed(1)}</span>
                    <span className="text-text-muted">${p.salary?.toLocaleString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

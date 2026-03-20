import React, { useState, useRef, useEffect } from 'react';

const QUICK_ACTIONS = [
  { label: '📋 Slate Overview', prompt: 'Give me a quick overview of today\'s slate. Which games have the highest implied totals?' },
  { label: '🔥 Top Stacks', prompt: 'What are the best team stacks today? Consider correlations and implied totals.' },
  { label: '💰 Value Plays', prompt: 'Find me the best value plays — players with high projected points relative to their salary.' },
  { label: '🎯 Contrarian', prompt: 'Suggest contrarian plays that will be low-owned but have high upside for GPPs.' },
  { label: '🌧️ Weather', prompt: 'Are there any weather concerns affecting today\'s games? How should I adjust?' },
  { label: '🏥 Injuries', prompt: 'What are the key injuries affecting today\'s slate and their DFS implications?' },
];

export default function CoPilotPanel({ isOpen, onClose, onAction }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isOpen]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text) => {
    if (!text.trim() || loading) return;

    const userMsg = { role: 'user', content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }));
      const res = await fetch('/api/copilot/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, history }),
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ ${e.message}` }]);
    }
    setLoading(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const parseActionButtons = (text) => {
    const parts = [];
    const regex = /\[ACTION:(lock|exclude):(\d+):([^\]]+)\]/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push({ type: 'text', content: text.slice(lastIndex, match.index) });
      }
      parts.push({
        type: 'action',
        action: match[1],
        playerId: parseInt(match[2]),
        playerName: match[3],
      });
      lastIndex = regex.lastIndex;
    }
    if (lastIndex < text.length) {
      parts.push({ type: 'text', content: text.slice(lastIndex) });
    }
    return parts;
  };

  const renderMessage = (msg, i) => {
    const isUser = msg.role === 'user';
    const parts = isUser ? [{ type: 'text', content: msg.content }] : parseActionButtons(msg.content);

    return (
      <div key={i} className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
        <div className={`max-w-[85%] px-3.5 py-2.5 rounded-xl border border-border text-[13px] leading-[1.5] text-text-primary whitespace-pre-wrap ${
          isUser ? 'bg-surface2' : 'bg-surface'
        }`}>
          {parts.map((part, j) => {
            if (part.type === 'action') {
              return (
                <button
                  key={j}
                  onClick={() => onAction && onAction(part.action, part.playerId)}
                  className={`inline-block m-1 mr-1 mb-1 px-2.5 py-1 rounded cursor-pointer bg-transparent text-xs font-semibold font-inherit ${
                    part.action === 'lock'
                      ? 'border border-venom text-venom'
                      : 'border border-red-400 text-red-400'
                  }`}
                >
                  {part.action === 'lock' ? '🔒' : '🚫'} {part.playerName}
                </button>
              );
            }
            return <span key={j}>{part.content}</span>;
          })}
        </div>
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <div className="fixed top-0 right-0 w-[380px] h-screen bg-primary border-l border-border flex flex-col z-[1000] shadow-[-4px_0_20px_rgba(0,0,0,0.5)]">
      {/* Header */}
      <div className="px-5 py-4 border-b border-border flex justify-between items-center">
        <div>
          <div className="text-sm font-bold text-venom">
            🤖 STACKSNIPER CoPilot
          </div>
          <div className="text-[10px] text-text-muted mt-0.5">
            AI-powered DFS assistant
          </div>
        </div>
        <button
          onClick={onClose}
          className="bg-transparent border-none text-text-muted text-lg cursor-pointer p-1 hover:text-text-primary transition-colors"
        >
          ✕
        </button>
      </div>

      {/* Quick Actions */}
      <div className="px-3 py-2.5 border-b border-border flex flex-wrap gap-1.5">
        {QUICK_ACTIONS.map((qa, i) => (
          <button
            key={i}
            onClick={() => sendMessage(qa.prompt)}
            className="px-2.5 py-1 rounded-xl text-[11px] bg-surface border border-border text-text-primary cursor-pointer font-inherit hover:border-venom/50 hover:text-venom transition-colors"
          >
            {qa.label}
          </button>
        ))}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="text-center text-text-muted text-xs mt-10">
            Ask me anything about your DFS slate.<br />
            Use the quick actions above to get started.
          </div>
        )}
        {messages.map(renderMessage)}
        {loading && (
          <div className="text-venom text-xs p-2">
            Thinking...
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="px-4 py-3 border-t border-border flex gap-2">
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your slate..."
          className="flex-1 px-3.5 py-2.5 rounded-lg bg-surface border border-border text-text-primary text-[13px] outline-none font-inherit focus:border-venom/50 transition-colors"
        />
        <button
          onClick={() => sendMessage(input)}
          disabled={loading || !input.trim()}
          className={`px-4 py-2.5 rounded-lg border-none bg-venom text-black font-bold text-[13px] cursor-pointer font-inherit transition-opacity ${
            loading || !input.trim() ? 'opacity-50 cursor-not-allowed' : 'hover:opacity-90'
          }`}
        >
          Send
        </button>
      </div>
    </div>
  );
}

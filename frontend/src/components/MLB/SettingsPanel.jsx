import React, { useState, useEffect } from 'react';

const API = '/api';

const SETTING_GROUPS = [
  {
    title: 'LLM Provider',
    fields: [
      { key: 'llm.provider', label: 'Provider', type: 'select', options: ['anthropic', 'openai', 'google'] },
      { key: 'llm.anthropic_api_key', label: 'Anthropic API Key', type: 'secret' },
      { key: 'llm.openai_api_key', label: 'OpenAI API Key', type: 'secret' },
      { key: 'llm.google_ai_api_key', label: 'Google AI Key', type: 'secret' },
      { key: 'llm.model', label: 'Model Override', type: 'text', placeholder: 'Leave blank for default' },
    ],
  },
  {
    title: 'Data Sources',
    fields: [
      { key: 'api_keys.the_odds_api_key', label: 'The Odds API Key', type: 'secret' },
      { key: 'api_keys.openweather_api_key', label: 'OpenWeatherMap Key', type: 'secret' },
    ],
  },
  {
    title: 'Simulation Defaults',
    fields: [
      { key: 'simulation.default_sim_count', label: 'Default Sim Count', type: 'number', min: 100, max: 10000 },
      { key: 'simulation.max_sim_count', label: 'Max Sim Count', type: 'number', min: 500, max: 10000 },
      { key: 'simulation.max_exposure', label: 'Max Exposure', type: 'number', min: 0.1, max: 1.0 },
    ],
  },
  {
    title: 'Dashboard & Optimizer',
    fields: [
      { key: 'dashboard.default_lineups', label: 'Default Lineups', type: 'number', min: 1, max: 150 },
      { key: 'simulation.contest_type', label: 'Contest Type', type: 'select', options: ['gpp', 'cash'] },
      { key: 'simulation.salary_cap', label: 'Salary Cap', type: 'number', min: 10000, max: 60000 },
    ],
  },
];

export default function SettingsPanel() {
  const [settings, setSettings] = useState({});
  const [status, setStatus] = useState({});
  const [saving, setSaving] = useState(false);
  const [testResults, setTestResults] = useState({});

  useEffect(() => {
    fetch(`${API}/settings`)
      .then(r => r.json())
      .then(d => setSettings(d.settings || {}))
      .catch(() => {});
  }, []);

  const getNestedValue = (obj, path) => {
    return path.split('.').reduce((o, k) => o?.[k], obj) ?? '';
  };

  const setNestedValue = (obj, path, value) => {
    const copy = JSON.parse(JSON.stringify(obj));
    const keys = path.split('.');
    let current = copy;
    for (let i = 0; i < keys.length - 1; i++) {
      if (!current[keys[i]]) current[keys[i]] = {};
      current = current[keys[i]];
    }
    current[keys[keys.length - 1]] = value;
    return copy;
  };

  const handleChange = (key, value) => {
    setSettings(prev => setNestedValue(prev, key, value));
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API}/settings`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings }),
      });
      const data = await res.json();
      setStatus({ type: 'success', message: 'Settings saved successfully' });
    } catch (e) {
      setStatus({ type: 'error', message: 'Failed to save settings' });
    }
    setSaving(false);
    setTimeout(() => setStatus({}), 3000);
  };

  const handleTestKey = async (provider) => {
    setTestResults(prev => ({ ...prev, [provider]: 'testing' }));
    try {
      const res = await fetch(`${API}/settings/test/${provider}`, { method: 'POST' });
      const data = await res.json();
      setTestResults(prev => ({ ...prev, [provider]: data.success ? 'ok' : 'fail' }));
    } catch {
      setTestResults(prev => ({ ...prev, [provider]: 'fail' }));
    }
    setTimeout(() => setTestResults(prev => ({ ...prev, [provider]: null })), 4000);
  };

  return (
    <div>
      <h3 className="text-text-muted text-xs tracking-widest mb-4">SETTINGS</h3>

      {status.message && (
        <div className={`px-4 py-2.5 rounded-lg mb-4 text-xs ${
          status.type === 'success'
            ? 'bg-green-900/30 border border-venom text-venom'
            : 'bg-red-900/30 border border-red-600 text-red-400'
        }`}>
          {status.message}
        </div>
      )}

      <div className="grid gap-5">
        {SETTING_GROUPS.map(group => (
          <div key={group.title} className="bg-surface rounded-lg p-5 border border-border">
            <h4 className="text-venom text-[13px] mb-3.5 uppercase">
              {group.title}
            </h4>
            <div className="grid gap-3">
              {group.fields.map(field => (
                <div key={field.key} className="flex items-center gap-3">
                  <label className="text-text-muted text-xs min-w-[160px]">
                    {field.label}
                  </label>
                  {field.type === 'select' ? (
                    <select
                      value={getNestedValue(settings, field.key) || ''}
                      onChange={e => handleChange(field.key, e.target.value)}
                      className="px-2.5 py-1.5 bg-surface2 border border-border/50 rounded-md text-text-primary font-mono text-xs outline-none flex-1"
                    >
                      {field.options.map(o => <option key={o} value={o}>{o}</option>)}
                    </select>
                  ) : field.type === 'secret' ? (
                    <div className="flex gap-1.5 flex-1">
                      <input
                        type="password"
                        value={getNestedValue(settings, field.key) || ''}
                        onChange={e => handleChange(field.key, e.target.value)}
                        placeholder="Enter API key..."
                        className="px-2.5 py-1.5 bg-surface2 border border-border/50 rounded-md text-text-primary font-mono text-xs outline-none flex-1 focus:border-venom/50 transition-colors"
                      />
                      {field.key.includes('anthropic_api') && (
                        <button
                          onClick={() => handleTestKey('anthropic')}
                          className="px-3.5 py-1.5 text-[10px] rounded-md font-mono font-semibold tracking-wider transition-all cursor-pointer bg-surface2 text-text-muted border border-border/50 hover:border-venom/50 hover:text-text-primary"
                        >
                          {testResults.anthropic === 'testing' ? '...' : testResults.anthropic === 'ok' ? '\u2713' : testResults.anthropic === 'fail' ? '\u2717' : 'Test'}
                        </button>
                      )}
                      {field.key.includes('openai_api') && (
                        <button
                          onClick={() => handleTestKey('openai')}
                          className="px-3.5 py-1.5 text-[10px] rounded-md font-mono font-semibold tracking-wider transition-all cursor-pointer bg-surface2 text-text-muted border border-border/50 hover:border-venom/50 hover:text-text-primary"
                        >
                          {testResults.openai === 'testing' ? '...' : testResults.openai === 'ok' ? '\u2713' : testResults.openai === 'fail' ? '\u2717' : 'Test'}
                        </button>
                      )}
                      {field.key.includes('google_ai') && (
                        <button
                          onClick={() => handleTestKey('google')}
                          className="px-3.5 py-1.5 text-[10px] rounded-md font-mono font-semibold tracking-wider transition-all cursor-pointer bg-surface2 text-text-muted border border-border/50 hover:border-venom/50 hover:text-text-primary"
                        >
                          {testResults.google === 'testing' ? '...' : testResults.google === 'ok' ? '\u2713' : testResults.google === 'fail' ? '\u2717' : 'Test'}
                        </button>
                      )}
                    </div>
                  ) : (
                    <input
                      type={field.type}
                      value={getNestedValue(settings, field.key) || ''}
                      onChange={e => handleChange(field.key, field.type === 'number' ? Number(e.target.value) : e.target.value)}
                      placeholder={field.placeholder || ''}
                      min={field.min}
                      max={field.max}
                      className="px-2.5 py-1.5 bg-surface2 border border-border/50 rounded-md text-text-primary font-mono text-xs outline-none flex-1 max-w-[150px] focus:border-venom/50 transition-colors"
                    />
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-5 flex gap-2.5">
        <button
          onClick={handleSave}
          disabled={saving}
          className="px-6 py-2.5 rounded-md font-mono text-xs font-semibold tracking-wider transition-all cursor-pointer bg-gradient-to-br from-venom to-venom-glow text-primary hover:opacity-90"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>
      </div>
    </div>
  );
}

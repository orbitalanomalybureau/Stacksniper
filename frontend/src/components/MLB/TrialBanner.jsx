import React, { useState, useEffect } from 'react';

function getDaysRemaining(trialEndDate) {
  if (!trialEndDate) return 0;
  const end = new Date(trialEndDate);
  const now = new Date();
  const diff = end.getTime() - now.getTime();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

export default function TrialBanner({ trialEndDate, onUpgrade }) {
  const [dismissed, setDismissed] = useState(false);
  const [daysLeft, setDaysLeft] = useState(() => getDaysRemaining(trialEndDate));

  // Check sessionStorage for dismissal (re-appears on next session)
  useEffect(() => {
    try {
      const dismissedThisSession = sessionStorage.getItem('stacksniper_trial_banner_dismissed');
      if (dismissedThisSession === 'true') {
        setDismissed(true);
      }
    } catch (e) { /* sessionStorage unavailable */ }
  }, []);

  // Update countdown
  useEffect(() => {
    setDaysLeft(getDaysRemaining(trialEndDate));
    const interval = setInterval(() => {
      setDaysLeft(getDaysRemaining(trialEndDate));
    }, 60000); // update every minute
    return () => clearInterval(interval);
  }, [trialEndDate]);

  const handleDismiss = () => {
    setDismissed(true);
    try {
      sessionStorage.setItem('stacksniper_trial_banner_dismissed', 'true');
    } catch (e) { /* */ }
  };

  if (dismissed || daysLeft <= 0) return null;

  const isUrgent = daysLeft <= 2;

  return (
    <div className={`flex items-center justify-center gap-4 px-5 py-2 text-[13px] relative ${
      isUrgent
        ? 'bg-gradient-to-r from-red-500/15 to-venom/15 border-b border-red-500/30'
        : 'bg-gradient-to-r from-venom/10 to-venom/5 border-b border-venom/20'
    }`}>
      {/* Icon */}
      <span className="text-sm">
        {isUrgent ? '\u23F3' : '\u2B50'}
      </span>

      {/* Message */}
      <span className="text-venom font-semibold">
        Pro Trial: {daysLeft} {daysLeft === 1 ? 'day' : 'days'} remaining
      </span>

      {/* Upgrade link */}
      <button
        onClick={onUpgrade}
        className="bg-transparent border border-venom rounded px-3 py-0.5 text-venom text-[11px] font-bold cursor-pointer tracking-wider transition-all duration-200 hover:bg-venom hover:text-primary"
      >
        UPGRADE NOW
      </button>

      {/* Dismiss button */}
      <button
        onClick={handleDismiss}
        className="absolute right-3 top-1/2 -translate-y-1/2 bg-transparent border-none text-text-muted cursor-pointer text-base px-1.5 py-0.5 leading-none"
        title="Dismiss"
      >
        {'\u00D7'}
      </button>
    </div>
  );
}

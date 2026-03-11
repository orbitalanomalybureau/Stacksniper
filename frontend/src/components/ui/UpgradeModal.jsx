import Modal from "./Modal";
import { Lock, Zap } from "lucide-react";
import { Link } from "react-router-dom";

export default function UpgradeModal({ open, onClose, feature, requiredTier = "pro" }) {
  const tierLabel = requiredTier.charAt(0).toUpperCase() + requiredTier.slice(1);

  return (
    <Modal open={open} onClose={onClose} size="sm">
      <div className="text-center py-4">
        <div className="w-16 h-16 rounded-full bg-venom/10 flex items-center justify-center mx-auto mb-4">
          <Lock className="w-8 h-8 text-venom" />
        </div>
        <h3 className="text-xl font-bold mb-2">Upgrade Required</h3>
        <p className="text-text-muted text-sm mb-6">
          {feature || "This feature"} requires a{" "}
          <span className="text-venom font-semibold">{tierLabel}</span> plan.
        </p>
        <div className="flex gap-3 justify-center">
          <button onClick={onClose} className="btn-ghost btn-sm">
            Maybe Later
          </button>
          <Link to="/pricing" onClick={onClose} className="btn-primary btn-sm flex items-center gap-1.5">
            <Zap className="w-4 h-4" /> Upgrade Now
          </Link>
        </div>
      </div>
    </Modal>
  );
}

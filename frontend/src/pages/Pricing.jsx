import { Check, Shield, Crown } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import apiClient from "../api/client";

const PLANS = [
  {
    name: "Free",
    tier: "free",
    price: "$0",
    period: "forever",
    features: [
      "Basic projections",
      "1,000 sim limit",
      "5 lineups per optimize",
      "10 requests/min",
    ],
    cta: "Current Plan",
    highlighted: false,
    elite: false,
    icon: null,
  },
  {
    name: "Pro",
    tier: "pro",
    price: "$19",
    period: "/month",
    features: [
      "Advanced projections",
      "25,000 sim limit",
      "50 lineups per optimize",
      "Correlation stacking",
      "60 requests/min",
      "7-day free trial",
    ],
    cta: "Upgrade to Pro",
    highlighted: true,
    elite: false,
    icon: Shield,
  },
  {
    name: "Elite",
    tier: "elite",
    price: "$49",
    period: "/month",
    features: [
      "Everything in Pro",
      "100,000 sim limit",
      "150 lineups per optimize",
      "Custom correlations",
      "Ownership projections",
      "200 requests/min",
      "Priority support",
    ],
    cta: "Go Elite",
    highlighted: false,
    elite: true,
    icon: Crown,
  },
];

export default function Pricing() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const handleSubscribe = async (tier) => {
    if (!user) {
      navigate("/register");
      return;
    }
    if (tier === "free" || tier === user?.tier) return;
    try {
      const { data } = await apiClient.post("/api/billing/create-checkout-session", { tier });
      window.location.href = data.url;
    } catch (err) {
      console.error("Checkout failed:", err);
    }
  };

  const getButtonText = (plan) => {
    if (user?.tier === plan.tier) return "Current Plan";
    return plan.cta;
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-20">
      <h1 className="text-3xl font-bold text-center mb-2">Choose Your Edge</h1>
      <p className="text-text-muted text-center mb-12">
        Scale your DFS game with the tools the pros use.
      </p>

      <div className="grid md:grid-cols-3 gap-6">
        {PLANS.map((plan) => {
          const Icon = plan.icon;
          return (
            <div
              key={plan.name}
              className={`card-hover flex flex-col ${
                plan.highlighted
                  ? "border-venom ring-1 ring-venom"
                  : plan.elite
                  ? "border-gold ring-1 ring-gold"
                  : ""
              }`}
            >
              {plan.highlighted && (
                <div className="badge-pro text-xs font-semibold px-3 py-1 rounded-full self-start mb-3">POPULAR</div>
              )}
              <div className="flex items-center gap-2 mb-1">
                {Icon && <Icon className={`w-5 h-5 ${plan.elite ? "text-gold" : "text-venom"}`} />}
                <h3 className="text-xl font-bold">{plan.name}</h3>
              </div>
              <div className="mb-4">
                <span className={`text-3xl font-bold ${plan.elite ? "text-gold" : "text-venom"}`}>{plan.price}</span>
                <span className="text-text-muted text-sm">{plan.period}</span>
              </div>
              <ul className="space-y-2 mb-6 flex-1">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-center gap-2 text-sm text-text-secondary">
                    <Check className={`w-4 h-4 flex-shrink-0 ${plan.elite ? "text-gold" : "text-venom"}`} />
                    {feature}
                  </li>
                ))}
              </ul>
              <button
                onClick={() => handleSubscribe(plan.tier)}
                disabled={user?.tier === plan.tier}
                className={`w-full ${
                  user?.tier === plan.tier
                    ? "bg-surface-lighter text-text-muted px-6 py-2 rounded-lg cursor-not-allowed"
                    : plan.highlighted
                    ? "btn-primary"
                    : "btn-secondary"
                }`}
              >
                {getButtonText(plan)}
              </button>
            </div>
          );
        })}
      </div>

      <p className="text-center text-xs text-text-muted/60 mt-8">
        Not gambling advice; for entertainment only. Please play responsibly.
      </p>
    </div>
  );
}

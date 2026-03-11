export default function Logo({ size = 36, className = "", glow = false }) {
  return (
    <div
      className={`relative inline-flex items-center justify-center rounded-full overflow-hidden ${className}`}
      style={{ width: size, height: size }}
    >
      {glow && (
        <div className="absolute inset-0 bg-venom/20 rounded-full blur-xl" />
      )}
      <img
        src="/logo.jpg"
        alt="Stack Sniper"
        width={size}
        height={size}
        className="relative rounded-full object-cover"
        style={{
          filter: "invert(1) hue-rotate(180deg) brightness(1.3) saturate(1.8)",
        }}
      />
    </div>
  );
}

export function TextLogo({ className = "" }) {
  return (
    <span className={`font-sans font-black tracking-tight ${className}`}>
      <span className="bg-gradient-to-r from-venom to-venom-glow bg-clip-text text-transparent">
        STACK
      </span>{" "}
      <span className="text-text-primary">SNIPER</span>
    </span>
  );
}

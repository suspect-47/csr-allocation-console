// YourDues brand mark — memoji-style capybara. Soft-shaded, rounded, with
// idle motion (bob, blink, ear-twitch) driven by classes in market.css.
export function Capybara({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true">
      <defs>
        <radialGradient id="capHead" cx="42%" cy="34%" r="72%">
          <stop offset="0%" stopColor="#c99566" />
          <stop offset="62%" stopColor="#ac7645" />
          <stop offset="100%" stopColor="#8a5a32" />
        </radialGradient>
        <radialGradient id="capMuz" cx="50%" cy="30%" r="80%">
          <stop offset="0%" stopColor="#b08356" />
          <stop offset="100%" stopColor="#8c5f38" />
        </radialGradient>
        <radialGradient id="capEar" cx="50%" cy="35%" r="75%">
          <stop offset="0%" stopColor="#97663c" />
          <stop offset="100%" stopColor="#6d4526" />
        </radialGradient>
      </defs>
      <g className="cap-bob">
        {/* ears */}
        <g className="cap-ear-l">
          <ellipse cx="16" cy="17" rx="7.5" ry="8.5" fill="url(#capEar)" />
          <ellipse cx="16" cy="18.5" rx="3.4" ry="4" fill="#502f18" opacity=".9" />
        </g>
        <g className="cap-ear-r">
          <ellipse cx="48" cy="17" rx="7.5" ry="8.5" fill="url(#capEar)" />
          <ellipse cx="48" cy="18.5" rx="3.4" ry="4" fill="#502f18" opacity=".9" />
        </g>
        {/* head */}
        <rect x="9" y="13" width="46" height="42" rx="21" fill="url(#capHead)" />
        {/* top gloss */}
        <ellipse cx="26" cy="22" rx="13" ry="7" fill="#fff" opacity=".14" />
        {/* cheek blush */}
        <ellipse cx="18" cy="38" rx="4.5" ry="3" fill="#d98f6a" opacity=".38" />
        <ellipse cx="46" cy="38" rx="4.5" ry="3" fill="#d98f6a" opacity=".38" />
        {/* eyes */}
        <g className="cap-eye cap-eye-l">
          <circle cx="23" cy="30" r="3.6" fill="#221610" />
          <circle cx="24.2" cy="28.7" r="1.2" fill="#fff" opacity=".9" />
        </g>
        <g className="cap-eye cap-eye-r">
          <circle cx="41" cy="30" r="3.6" fill="#221610" />
          <circle cx="42.2" cy="28.7" r="1.2" fill="#fff" opacity=".9" />
        </g>
        {/* muzzle */}
        <rect x="19" y="35" width="26" height="18" rx="9" fill="url(#capMuz)" />
        <ellipse cx="28" cy="42" rx="2.6" ry="2" fill="#241811" />
        <ellipse cx="36" cy="42" rx="2.6" ry="2" fill="#241811" />
        <path d="M29 48 q3 2.6 6 0" stroke="#241811" strokeWidth="1.4" strokeLinecap="round" fill="none" opacity=".7" />
      </g>
    </svg>
  );
}

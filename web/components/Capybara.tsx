// YourDues brand mark — a stylized capybara face (inline SVG, scalable).
export function Capybara({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true">
      {/* ears */}
      <ellipse cx="17" cy="18" rx="6.5" ry="7.5" fill="#8a5c34" />
      <ellipse cx="47" cy="18" rx="6.5" ry="7.5" fill="#8a5c34" />
      <ellipse cx="17" cy="19" rx="3" ry="3.6" fill="#5c3d22" />
      <ellipse cx="47" cy="19" rx="3" ry="3.6" fill="#5c3d22" />
      {/* head */}
      <rect x="11" y="15" width="42" height="38" rx="18" fill="#b07d4f" />
      <path d="M11 36 q0 17 21 17 q21 0 21-17" fill="#a06f43" opacity=".55" />
      {/* eyes */}
      <circle cx="23.5" cy="30" r="2.9" fill="#2e2016" />
      <circle cx="40.5" cy="30" r="2.9" fill="#2e2016" />
      <circle cx="24.4" cy="29.1" r=".9" fill="#fff" opacity=".85" />
      <circle cx="41.4" cy="29.1" r=".9" fill="#fff" opacity=".85" />
      {/* muzzle */}
      <rect x="20" y="35" width="24" height="17" rx="8.5" fill="#8a6038" />
      <ellipse cx="28.5" cy="42" rx="2.4" ry="1.9" fill="#2e2016" />
      <ellipse cx="35.5" cy="42" rx="2.4" ry="1.9" fill="#2e2016" />
    </svg>
  );
}

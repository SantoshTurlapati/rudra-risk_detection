import React from 'react';

interface BrandLogoProps {
  variant?: 'dark' | 'light';
  size?: 'sm' | 'md' | 'lg';
  showTagline?: boolean;
}

export const BrandLogo: React.FC<BrandLogoProps> = ({
  variant = 'light',
  size = 'md',
  showTagline = true
}) => {
  const isDark = variant === 'dark';

  return (
    <div className="flex items-center gap-3">
      {/* 3D Cyber Shield Emblem */}
      <div className="relative flex-shrink-0 flex items-center justify-center">
        <svg
          className={size === 'sm' ? 'w-8 h-8' : size === 'lg' ? 'w-12 h-12' : 'w-10 h-10'}
          viewBox="0 0 48 48"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <defs>
            <linearGradient id="shieldGrad" x1="4" y1="4" x2="44" y2="44" gradientUnits="userSpaceOnUse">
              <stop stopColor="#06C8F9" />
              <stop offset="0.5" stopColor="#0B8FFF" />
              <stop offset="1" stopColor="#087CF0" />
            </linearGradient>
            <linearGradient id="shieldInner" x1="12" y1="10" x2="36" y2="38" gradientUnits="userSpaceOnUse">
              <stop stopColor="#00479A" />
              <stop offset="1" stopColor="#041E42" />
            </linearGradient>
            <filter id="shieldGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#06C8F9" floodOpacity="0.4" />
            </filter>
          </defs>
          {/* Outer Shield with Glow */}
          <path
            d="M24 3L8 10V22C8 32.5 14.8 42.2 24 45C33.2 42.2 40 32.5 40 22V10L24 3Z"
            fill="url(#shieldGrad)"
            filter="url(#shieldGlow)"
          />
          {/* Inner Shield Contour */}
          <path
            d="M24 7L12 12.2V22C12 30.2 17.1 37.8 24 40.2C30.9 37.8 36 30.2 36 22V12.2L24 7Z"
            fill="url(#shieldInner)"
          />
          {/* Glowing Keyhole / Cyber Core */}
          <circle cx="24" cy="20" r="4.5" fill="#06C8F9" />
          <path d="M21.5 22L20 31H28L26.5 22H21.5Z" fill="#06C8F9" />
          <circle cx="24" cy="20" r="2.2" fill="#FFFFFF" />
        </svg>
      </div>

      {/* Brand Text & Tagline */}
      <div>
        <div className="flex items-center">
          <span className={`font-bold tracking-tight text-xl ${isDark ? 'text-white' : 'text-[#061A3A]'}`}>
            RudraShield
          </span>
          <span className="font-bold tracking-tight text-xl text-[#087CF0] ml-1.5">
            AI
          </span>
        </div>
        {showTagline && (
          <p className={`text-[10px] leading-tight font-medium ${isDark ? 'text-[#8E9EB5]' : 'text-[#657792]'}`}>
            Detect Deception. Expose Threats. Protect Digital Trust.
          </p>
        )}
      </div>
    </div>
  );
};

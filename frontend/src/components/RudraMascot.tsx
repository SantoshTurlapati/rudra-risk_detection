import React from 'react';

export const RudraMascot: React.FC<{ className?: string }> = ({ className = 'w-12 h-12' }) => {
  return (
    <div className={`relative flex items-center justify-center flex-shrink-0 ${className}`}>
      <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg" className="w-full h-full drop-shadow-md">
        {/* Antennas */}
        <circle cx="32" cy="6" r="3" fill="#06C8F9" />
        <line x1="32" y1="9" x2="32" y2="15" stroke="#087CF0" strokeWidth="2.5" />
        <circle cx="16" cy="18" r="2.5" fill="#087CF0" />
        <circle cx="48" cy="18" r="2.5" fill="#087CF0" />

        {/* Head Shell */}
        <rect x="14" y="14" width="36" height="26" rx="12" fill="#FFFFFF" stroke="#DCE7F5" strokeWidth="2" />
        {/* Visor Screen */}
        <rect x="19" y="19" width="26" height="15" rx="6" fill="#061A3A" />
        {/* Glowing Friendly Eyes */}
        <circle cx="26" cy="26" r="3" fill="#06C8F9" />
        <circle cx="38" cy="26" r="3" fill="#06C8F9" />
        {/* Smile Arc */}
        <path d="M29 29C30.5 30.5 33.5 30.5 35 29" stroke="#00E5FF" strokeWidth="1.5" strokeLinecap="round" />

        {/* Body */}
        <path d="M20 42C20 40 44 40 44 42L46 54C46 58 18 58 18 54L20 42Z" fill="#F1F7FF" stroke="#DCE7F5" strokeWidth="1.5" />

        {/* Little Shield Held in Left Hand */}
        <path d="M42 43L48 45V51C48 54 44 56 42 57C40 56 36 54 36 51V45L42 43Z" fill="#087CF0" />
        <path d="M42 45L46 46V50C46 52 43 54 42 54.5C41 54 38 52 38 50V46L42 45Z" fill="#06C8F9" />
      </svg>
    </div>
  );
};

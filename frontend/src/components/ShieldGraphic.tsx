import React from 'react';
import { Globe, User, MessageSquare, Image as ImageIcon, Link2, Smartphone } from 'lucide-react';

export const ShieldGraphic: React.FC = () => {
  return (
    <div className="relative w-full max-w-[500px] h-[360px] flex items-center justify-center my-4 select-none">
      {/* Background City Silhouette Vector */}
      <div className="absolute inset-x-0 bottom-12 h-36 opacity-25 flex items-end justify-between overflow-hidden px-4 pointer-events-none">
        <div className="w-8 h-28 bg-[#0B8FFF] rounded-t-sm" />
        <div className="w-12 h-32 bg-[#087CF0] rounded-t-sm" />
        <div className="w-10 h-20 bg-[#06C8F9] rounded-t-sm" />
        <div className="w-14 h-36 bg-[#087CF0] rounded-t-sm" />
        <div className="w-8 h-24 bg-[#0B8FFF] rounded-t-sm" />
        <div className="w-12 h-30 bg-[#06C8F9] rounded-t-sm" />
        <div className="w-10 h-20 bg-[#087CF0] rounded-t-sm" />
      </div>

      {/* Cyber Network Grid Rings / Holographic Pedestal */}
      <div className="absolute bottom-6 w-80 h-28 border-4 border-[#06C8F9]/50 rounded-[100%] shadow-[0_0_35px_rgba(6,200,249,0.5)] bg-gradient-to-t from-[#06C8F9]/20 to-transparent transform rotate-x-60" />
      <div className="absolute bottom-10 w-64 h-20 border-2 border-[#0B8FFF]/70 rounded-[100%] shadow-[0_0_20px_rgba(11,143,255,0.6)]" />
      <div className="absolute bottom-14 w-44 h-14 border border-[#00E5FF] rounded-[100%] bg-[#087CF0]/20 backdrop-blur-sm" />

      {/* Main Glowing 3D Shield with 'R' */}
      <div className="relative z-10 transform -translate-y-4 flex flex-col items-center">
        <div className="relative w-36 h-44 drop-shadow-[0_15px_30px_rgba(8,124,240,0.5)]">
          <svg viewBox="0 0 100 120" className="w-full h-full filter drop-shadow-[0_0_15px_rgba(6,200,249,0.7)]">
            <defs>
              <linearGradient id="shield3D" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#00E5FF" />
                <stop offset="30%" stopColor="#06C8F9" />
                <stop offset="70%" stopColor="#0B8FFF" />
                <stop offset="100%" stopColor="#0052CC" />
              </linearGradient>
              <linearGradient id="shieldCore3D" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#062B66" />
                <stop offset="100%" stopColor="#031633" />
              </linearGradient>
            </defs>
            {/* Outer Bevel */}
            <path
              d="M50 4 L14 18 V55 C14 85 50 114 50 114 C50 114 86 85 86 55 V18 L50 4 Z"
              fill="url(#shield3D)"
              stroke="#E0F7FF"
              strokeWidth="1.5"
            />
            {/* Inner Recessed Core */}
            <path
              d="M50 14 L24 24 V54 C24 78 50 102 50 102 C50 102 76 78 76 54 V24 L50 14 Z"
              fill="url(#shieldCore3D)"
            />
            {/* Embossed Letter 'R' */}
            <text
              x="50"
              y="74"
              fontSize="52"
              fontWeight="900"
              fill="#FFFFFF"
              textAnchor="middle"
              fontFamily="Inter, sans-serif"
              className="drop-shadow-[0_2px_8px_rgba(6,200,249,0.9)]"
            >
              R
            </text>
          </svg>
        </div>
      </div>

      {/* Orbiting Floating Cards Matching Reference B */}
      {/* 1. Profile Avatar (Top Left) */}
      <div className="absolute top-12 left-10 z-20 bg-gradient-to-br from-[#0B8FFF] to-[#087CF0] p-2.5 rounded-xl shadow-lg shadow-blue-500/30 border border-white/40 transform -rotate-6 hover:scale-110 transition-transform">
        <User className="w-5 h-5 text-white" />
      </div>

      {/* 2. Globe / Web (Top Right) */}
      <div className="absolute top-10 right-14 z-20 bg-gradient-to-br from-[#087CF0] to-[#041E42] p-2.5 rounded-xl shadow-lg shadow-blue-500/30 border border-cyan-400/50 transform rotate-6 hover:scale-110 transition-transform">
        <Globe className="w-5 h-5 text-cyan-300" />
      </div>

      {/* 3. Image Photo (Middle Left) */}
      <div className="absolute top-36 left-4 z-20 bg-gradient-to-br from-[#06C8F9] to-[#087CF0] p-2.5 rounded-xl shadow-lg shadow-cyan-500/30 border border-white/40 transform -rotate-12 hover:scale-110 transition-transform">
        <ImageIcon className="w-5 h-5 text-white" />
      </div>

      {/* 4. Chat Message (Middle Right) */}
      <div className="absolute top-32 right-6 z-20 bg-gradient-to-br from-[#0B8FFF] to-[#041E42] p-2.5 rounded-xl shadow-lg shadow-blue-500/30 border border-white/40 transform rotate-8 hover:scale-110 transition-transform">
        <MessageSquare className="w-5 h-5 text-white" />
      </div>

      {/* 5. Hyperlink Chain (Bottom Left) */}
      <div className="absolute bottom-14 left-14 z-20 bg-gradient-to-br from-[#0066FF] to-[#041832] p-2.5 rounded-xl shadow-lg shadow-blue-500/30 border border-white/40 transform -rotate-3 hover:scale-110 transition-transform">
        <Link2 className="w-5 h-5 text-white" />
      </div>

      {/* 6. Mobile App (Bottom Right) */}
      <div className="absolute bottom-16 right-16 z-20 bg-gradient-to-br from-[#087CF0] to-[#041832] p-2.5 rounded-xl shadow-lg shadow-blue-500/30 border border-white/40 transform rotate-12 hover:scale-110 transition-transform">
        <Smartphone className="w-5 h-5 text-white" />
      </div>
    </div>
  );
};

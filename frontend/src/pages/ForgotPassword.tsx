import React from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, ArrowLeft } from 'lucide-react';
import { BrandLogo } from '../components/BrandLogo';

export const ForgotPassword: React.FC = () => (
  <div className="min-h-screen w-full bg-gradient-to-br from-[#E6F2FF] via-[#F1F7FF] to-[#DDF1FF] flex items-center justify-center p-4 font-sans">
    <div className="w-full max-w-md bg-white rounded-[28px] shadow-lg border border-[#DCE7F5] p-8">
      <div className="mb-6 flex justify-center">
        <BrandLogo size="md" variant="light" />
      </div>
      <div className="text-center space-y-4">
        <AlertTriangle className="w-10 h-10 text-amber-600 mx-auto" />
        <h3 className="text-xl font-bold text-[#102447]">Password Recovery Unavailable</h3>
        <p className="text-xs text-[#657792] leading-relaxed">
          Secure password-reset token delivery is not configured. Contact your organization administrator
          to regain access. No reset request or password change has been made.
        </p>
        <Link to="/login" className="text-xs font-bold text-[#087CF0] hover:underline flex items-center justify-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Login
        </Link>
      </div>
    </div>
  </div>
);

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Mail, Lock, User, Building, Eye, EyeOff, ShieldCheck, ArrowRight } from 'lucide-react';
import { BrandLogo } from '../components/BrandLogo';
import { api } from '../services/api';
import { apiErrorMessage } from '../utils/apiErrorMessage';

export const Register: React.FC = () => {
  const navigate = useNavigate();
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [organization, setOrganization] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Password strength logic
  const getPasswordStrength = () => {
    let score = 0;
    if (password.length >= 8) score++;
    if (/[A-Z]/.test(password)) score++;
    if (/[0-9]/.test(password)) score++;
    if (/[^A-Za-z0-9]/.test(password)) score++;
    return score;
  };

  const strength = getPasswordStrength();

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!termsAccepted) {
      setError('Please accept the Terms of Service & Privacy Policy.');
      return;
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    if (password.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (loading) return;

    setLoading(true);
    setError('');
    try {
      await api.register({
        full_name: fullName,
        email,
        organization_name: organization || 'Cyber Defense Org',
        password
      });
      navigate('/login');
    } catch (err) {
      setError(apiErrorMessage(err, 'Registration failed. Please check inputs.'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-[#E6F2FF] via-[#F1F7FF] to-[#DDF1FF] flex items-center justify-center p-4 sm:p-6 font-sans">
      <div className="w-full max-w-lg bg-white rounded-[28px] shadow-[0_12px_40px_rgba(6,26,58,0.08)] border border-[#DCE7F5] p-7 sm:p-9">
        <div className="mb-6 flex justify-center">
          <BrandLogo size="md" variant="light" />
        </div>

        <div className="text-center mb-6">
          <h2 className="text-2xl font-bold text-[#102447]">Create Your Account</h2>
          <p className="text-xs text-[#657792] mt-1">Join the enterprise digital risk defense network</p>
        </div>

        {error && (
          <div role="alert" className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-xl text-xs">
            {error}
          </div>
        )}

        <form onSubmit={handleRegister} className="space-y-3.5">
          {/* Full Name */}
          <div className="relative">
            <User className="w-4 h-4 text-[#8E9EB5] absolute left-3.5 top-3.5" />
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Full Name (e.g. Shaik Yasmine)"
              className="w-full pl-10 pr-4 py-2.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-sm text-[#102447] focus:outline-none focus:border-[#087CF0]"
            />
          </div>

          {/* Email */}
          <div className="relative">
            <Mail className="w-4 h-4 text-[#8E9EB5] absolute left-3.5 top-3.5" />
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Corporate Email Address"
              className="w-full pl-10 pr-4 py-2.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-sm text-[#102447] focus:outline-none focus:border-[#087CF0]"
            />
          </div>

          {/* Organization */}
          <div className="relative">
            <Building className="w-4 h-4 text-[#8E9EB5] absolute left-3.5 top-3.5" />
            <input
              type="text"
              value={organization}
              onChange={(e) => setOrganization(e.target.value)}
              placeholder="Organization / Agency Name"
              className="w-full pl-10 pr-4 py-2.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-sm text-[#102447] focus:outline-none focus:border-[#087CF0]"
            />
          </div>

          {/* Password */}
          <div className="relative">
            <Lock className="w-4 h-4 text-[#8E9EB5] absolute left-3.5 top-3.5" />
            <input
              type={showPassword ? 'text' : 'password'}
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password (minimum 8 characters)"
              className="w-full pl-10 pr-10 py-2.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-sm text-[#102447] focus:outline-none focus:border-[#087CF0]"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3.5 top-3.5 text-[#8E9EB5]"
            >
              {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            </button>
          </div>

          {/* Password Strength Meter */}
          {password && (
            <div className="space-y-1">
              <div className="flex gap-1 h-1.5 w-full">
                <div className={`h-full rounded flex-1 ${strength >= 1 ? 'bg-red-400' : 'bg-gray-200'}`} />
                <div className={`h-full rounded flex-1 ${strength >= 2 ? 'bg-orange-400' : 'bg-gray-200'}`} />
                <div className={`h-full rounded flex-1 ${strength >= 3 ? 'bg-yellow-400' : 'bg-gray-200'}`} />
                <div className={`h-full rounded flex-1 ${strength >= 4 ? 'bg-emerald-500' : 'bg-gray-200'}`} />
              </div>
              <p className="text-[10px] text-[#657792]">
                Strength: {strength <= 1 ? 'Weak' : strength <= 3 ? 'Medium' : 'Strong & Secure'}
              </p>
            </div>
          )}

          {/* Confirm Password */}
          <div className="relative">
            <Lock className="w-4 h-4 text-[#8E9EB5] absolute left-3.5 top-3.5" />
            <input
              type={showPassword ? 'text' : 'password'}
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Confirm Password"
              className="w-full pl-10 pr-4 py-2.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-sm text-[#102447] focus:outline-none focus:border-[#087CF0]"
            />
          </div>

          {/* Terms checkbox */}
          <div className="flex items-center gap-2 pt-1">
            <input
              type="checkbox"
              id="terms"
              checked={termsAccepted}
              onChange={(e) => setTermsAccepted(e.target.checked)}
              className="rounded border-[#DCE7F5] text-[#087CF0] focus:ring-[#087CF0]"
            />
            <label htmlFor="terms" className="text-xs text-[#657792]">
              I acknowledge the <span className="text-[#087CF0] font-semibold">Terms of Service</span> and Responsible AI Ethics
            </label>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 bg-gradient-to-r from-[#087CF0] to-[#06C8F9] hover:from-[#076ecc] hover:to-[#05b8e5] text-white font-semibold rounded-xl text-sm shadow-md shadow-blue-500/25 flex items-center justify-center gap-2 transition-all mt-4"
          >
            {loading ? 'Creating Account...' : (
              <>
                <span>Complete Registration</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        <div className="mt-5 text-center">
          <span className="text-xs text-[#657792]">Already have an account? </span>
          <Link to="/login" className="text-xs font-bold text-[#087CF0] hover:underline">
            Sign In ➔
          </Link>
        </div>
      </div>
    </div>
  );
};

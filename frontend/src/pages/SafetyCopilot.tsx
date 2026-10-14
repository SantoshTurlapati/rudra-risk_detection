import React, { useState, useRef, useEffect } from 'react';
import { Sparkles, Send, Globe, ShieldCheck, AlertTriangle, ArrowRight } from 'lucide-react';
import { RudraMascot } from '../components/RudraMascot';
import { api } from '../services/api';

interface Message {
  sender: 'user' | 'rudra';
  text: string;
  tips?: string[];
  actions?: string[];
  assessment?: string;
}

export const SafetyCopilot: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      sender: 'rudra',
      text: "Hello! I'm Rudra, a rule-based cybersecurity safety guide. I provide general guidance about suspicious links, fake profiles, APK risks, and reporting cyber scams in English or Telugu. I don't analyze your message or check live threat data.",
      tips: [
        "Never share OTP or banking passwords over SMS/phone.",
        "Verify domain names carefully: e.g. 'sbi-verify.net' vs 'onlinesbi.sbi'."
      ],
      actions: [
        "Analyze a link in Investigate",
        "Report cyber fraud to Helpline 1930"
      ]
    }
  ]);
  const [input, setInput] = useState('');
  const [language, setLanguage] = useState<'en' | 'te'>('en');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (textToSend?: string) => {
    const q = textToSend || input;
    if (!q.trim()) return;

    const userMsg: Message = { sender: 'user', text: q };
    setMessages(prev => [...prev, userMsg]);
    if (!textToSend) setInput('');
    setLoading(true);

    try {
      const data = await api.copilotChat(q, language);
      const rudraMsg: Message = {
        sender: 'rudra',
        text: data.reply,
        tips: data.safety_tips,
        actions: data.suggested_actions,
        assessment: data.risk_assessment
      };
      setMessages(prev => [...prev, rudraMsg]);
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          sender: 'rudra',
          text: "I am having trouble connecting to the intelligence server right now. Please check if the FastAPI backend is running."
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto">

      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <RudraMascot className="w-12 h-12" />
          <div>
            <h1 className="text-xl font-bold text-[#102447] flex items-center gap-2">
              Safety Copilot Assistant
            </h1>
            <p className="text-xs text-[#657792]">
              Keyword-triggered safety guidance; messages and live threats are not analyzed
            </p>
          </div>
        </div>

        {/* Language Toggle */}
        <div className="flex items-center gap-2 bg-white px-3 py-1.5 rounded-xl border border-[#DCE7F5] shadow-sm">
          <Globe className="w-4 h-4 text-[#087CF0]" />
          <button
            onClick={() => setLanguage('en')}
            className={`text-xs font-bold px-2.5 py-1 rounded-lg transition-all ${
              language === 'en' ? 'bg-[#087CF0] text-white shadow-sm' : 'text-[#657792]'
            }`}
          >
            English
          </button>
          <button
            onClick={() => setLanguage('te')}
            className={`text-xs font-bold px-2.5 py-1 rounded-lg transition-all ${
              language === 'te' ? 'bg-[#087CF0] text-white shadow-sm' : 'text-[#657792]'
            }`}
          >
            తెలుగు
          </button>
        </div>
      </div>

      {/* Main Chat Interface */}
      <div className="bg-white rounded-2xl border border-[#DCE7F5] shadow-card flex flex-col h-[600px] overflow-hidden">

        {/* Messages Scroll Area */}
        <div className="flex-1 p-6 overflow-y-auto space-y-4 bg-[#F8FAFC]">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex gap-3 ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {m.sender === 'rudra' && (
                <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <RudraMascot className="w-6 h-6" />
                </div>
              )}

              <div className={`max-w-xl rounded-2xl p-4 text-xs space-y-3 leading-relaxed ${
                m.sender === 'user'
                  ? 'bg-[#087CF0] text-white font-medium rounded-br-none shadow-md shadow-blue-500/20'
                  : 'bg-white border border-[#DCE7F5] text-[#102447] rounded-bl-none shadow-sm'
              }`}>
                <p>{m.text}</p>

                {m.assessment && (
                  <div className="inline-block px-2.5 py-1 rounded-md bg-amber-50 border border-amber-200 text-amber-800 font-bold text-[10px]">
                    {m.assessment}
                  </div>
                )}

                {/* Safety Tips if available */}
                {m.tips && m.tips.length > 0 && (
                  <div className="pt-2 border-t border-gray-100 space-y-1 text-[11px] text-[#657792]">
                    <p className="font-bold text-[#102447]">Safety Precautions:</p>
                    <ul className="list-disc pl-4 space-y-0.5">
                      {m.tips.map((t, i) => <li key={i}>{t}</li>)}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-2 text-xs text-[#657792]">
              <RudraMascot className="w-5 h-5 animate-bounce" />
              <span>Preparing general safety guidance...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Quick Query Pills */}
        <div className="p-3 bg-white border-t border-[#DCE7F5] flex flex-wrap gap-2 text-[11px]">
          <button
            onClick={() => handleSend(language === 'te' ? "ఈ KYC లింక్ నన్ను OTP అడుగుతోంది, ఇది సురక్షితమేనా?" : "Why is this KYC link asking for my OTP?")}
            className="px-3 py-1 bg-[#F1F7FF] text-[#087CF0] hover:bg-[#E1EFFF] rounded-full font-semibold border border-[#D0E4FA] transition-colors"
          >
            {language === 'te' ? "KYC లింక్ & OTP రిస్క్" : "Why is KYC link asking for OTP?"}
          </button>
          <button
            onClick={() => handleSend(language === 'te' ? "నకిలీ సోషల్ మీడియా ప్రొఫైల్‌ను ఎలా గుర్తించాలి?" : "How do I recognize a fake bank Twitter account?")}
            className="px-3 py-1 bg-[#F1F7FF] text-[#087CF0] hover:bg-[#E1EFFF] rounded-full font-semibold border border-[#D0E4FA] transition-colors"
          >
            {language === 'te' ? "నకిలీ సోషల్ ప్రొఫైల్స్" : "Recognize fake bank accounts"}
          </button>
          <button
            onClick={() => handleSend(language === 'te' ? "వాట్సాప్‌లో వచ్చిన APK ఫైల్ ప్రమాదకరమా?" : "What does an app-publisher mismatch mean?")}
            className="px-3 py-1 bg-[#F1F7FF] text-[#087CF0] hover:bg-[#E1EFFF] rounded-full font-semibold border border-[#D0E4FA] transition-colors"
          >
            {language === 'te' ? "APK యాప్ మోసాలు" : "App publisher mismatch"}
          </button>
        </div>

        {/* Chat Input Bar */}
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="p-4 bg-white border-t border-[#DCE7F5] flex items-center gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={language === 'te' ? "అనుమానాస్పద లింక్, యాప్ లేదా సందేశం గురించి అడగండి..." : "Ask Rudra about suspicious links, apps, or scam messages..."}
            className="flex-1 px-4 py-2.5 bg-[#F8FAFC] border border-[#DCE7F5] rounded-xl text-xs text-[#102447] focus:outline-none focus:border-[#087CF0]"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-4 py-2.5 bg-[#087CF0] hover:bg-[#076ecc] disabled:opacity-50 text-white rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-md shadow-blue-500/20 transition-all"
          >
            <span>Send</span>
            <Send className="w-3.5 h-3.5" />
          </button>
        </form>

      </div>

    </div>
  );
};

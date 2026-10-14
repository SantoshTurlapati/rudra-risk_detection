/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#087CF0',
          hover: '#076ecc',
          bright: '#0B8FFF',
        },
        cyan: {
          accent: '#06C8F9',
        },
        navy: {
          sidebar: '#041832',
          dark: '#061A3A',
          card: '#0a2347',
        },
        brandBg: '#F1F7FF',
        brandText: {
          DEFAULT: '#102447',
          secondary: '#657792',
          muted: '#8e9eb5',
        },
        brandBorder: '#DCE7F5',
        status: {
          success: '#12B981',
          warning: '#F59E0B',
          danger: '#EF4444',
          purple: '#8B5CF6',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'card': '0 2px 10px rgba(6, 26, 58, 0.04)',
        'card-hover': '0 8px 24px rgba(8, 124, 240, 0.08)',
        'glow-blue': '0 0 20px rgba(8, 124, 240, 0.4)',
        'glow-cyan': '0 0 20px rgba(6, 200, 249, 0.4)',
      }
    },
  },
  plugins: [],
}

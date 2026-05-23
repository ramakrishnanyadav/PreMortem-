/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bgDark: '#050810',
        bgPanel: '#0a0f1e',
        bgHover: '#0d1526',
        borderTheme: '#1a2744',
        borderActive: '#1e3a6e',
        healthy: '#00d4aa',
        warning: '#f59e0b',
        critical: '#ef4444',
        predicting: '#6366f1',
        unknown: '#4b5563',
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      }
    },
  },
  plugins: [],
}

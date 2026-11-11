/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#0B132B',
          800: '#0F172A',
          700: '#1E293B',
          600: '#334155',
        },
        brand: {
          50: '#EFF6FF',
          100: '#DBEAFE',
          500: '#3B82F6',
          600: '#2563EB',
          700: '#1D4ED8',
        },
        shark: {
          accent: '#0EA5E9',
          success: '#10B981',
          warning: '#F59E0B',
          danger: '#EF4444',
        }
      },
    },
  },
  plugins: [],
}

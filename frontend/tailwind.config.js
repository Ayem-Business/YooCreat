/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          blue: '#3B82F6',
          'blue-dark': '#1E40AF',
          violet: '#8B5CF6',
          'violet-dark': '#6D28D9',
          orange: '#F97316',
          'orange-dark': '#EA580C',
        },
      },
    },
  },
  plugins: [],
}
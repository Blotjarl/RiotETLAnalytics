/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      // --- ADD THIS ---
      keyframes: {
        'progress': {
          '0%': { width: '0%' },
          '100%': { width: '100%' },
        }
      },
      animation: {
        // This animation will take 3 minutes (180s) to complete
        'progress': 'progress 360s linear forwards',
      }
      // --- END ADD ---
    },
  },
  plugins: [],
}
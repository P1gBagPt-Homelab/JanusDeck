/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{svelte,js,ts}'],
  theme: {
    extend: {
      colors: {
        ground: '#0b0f19',
        surface: {
          DEFAULT: '#111827',
          elevated: '#162036',
          hover: '#1e2a47',
        },
        cyan: {
          accent: '#38bdf8',
        },
        indigo: {
          accent: '#6366f1',
        },
        emerald: {
          accent: '#34d399',
        },
        amber: {
          accent: '#fbbf24',
        },
        rose: {
          accent: '#f43f5e',
        },
      },
    },
  },
  plugins: [],
};

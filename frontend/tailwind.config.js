/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        ox: { DEFAULT: '#002147', 50: '#eef3f9', 100: '#d6e2f0', 600: '#0b3b73', 700: '#002147' },
        leaf: { DEFAULT: '#2f8f5b', 50: '#ebf7f0', 100: '#cdebd9', 600: '#24744a' },
        amberx: '#c27c0e',
      },
      fontFamily: { sans: ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'sans-serif'] },
    },
  },
  plugins: [],
}

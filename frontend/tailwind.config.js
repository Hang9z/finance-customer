/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        paper: '#F6F4EF',
        surface: '#FFFFFF',
        ink: '#14171C',
        'ink-2': '#5B616B',
        hairline: '#E4E0D6',
        seal: '#B5432F',
        celadon: '#3F6F68',
        amber: '#B7791F',
        mist: '#9AA0A8',
      },
      fontFamily: {
        serif: ['"Noto Serif SC"', '"Source Han Serif SC"', '"Songti SC"', 'serif'],
        sans: ['"Inter"', '"PingFang SC"', '"Microsoft YaHei"', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"SFMono-Regular"', 'Consolas', 'monospace'],
      },
      boxShadow: {
        ledger: '0 1px 2px rgba(20,23,28,.04), 0 6px 20px -10px rgba(20,23,28,.12)',
      },
    },
  },
  plugins: [],
};

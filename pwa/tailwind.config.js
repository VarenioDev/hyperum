/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Montserrat Alternates"', 'system-ui', 'sans-serif'],
      },
      colors: {
        // Клубнично-пурпурная палитра HyperUm
        brand: {
          50:  '#fdf2f8',   // очень светлый розовый
          100: '#fce7f3',
          200: '#fbcfe8',
          300: '#f9a8d4',
          400: '#f472b6',
          500: '#ec4899',   // основной
          600: '#db2777',
          700: '#be185d',
          800: '#9d174d',
          900: '#831843',
        },
        purple: {
          50:  '#faf5ff',
          100: '#f3e8ff',
          200: '#e9d5ff',
          300: '#d8b4fe',
          400: '#c084fc',
          500: '#a855f7',
          600: '#9333ea',
          700: '#7e22ce',
          800: '#6b21a8',
          900: '#581c87',
        },
        mastery: {
          strong:  '#22c55e',
          medium:  '#eab308',
          weak:    '#ef4444',
          unknown: '#cbd5e1',
        },
      },
      backgroundImage: {
        // Основной градиент HyperUm
        'hyper': 'linear-gradient(135deg, #ec4899 0%, #a855f7 100%)',
        'hyper-soft': 'linear-gradient(135deg, #fce7f3 0%, #f3e8ff 100%)',
        'hyper-vivid': 'linear-gradient(135deg, #f472b6 0%, #c084fc 50%, #a855f7 100%)',
      },
    },
  },
  plugins: [],
}
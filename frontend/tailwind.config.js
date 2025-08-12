/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "./public/index.html"
  ],
  theme: {
    extend: {
      boxShadow: {
        soft: "0 6px 18px rgba(0,0,0,0.06)",
      },
      borderRadius: {
        xl: "1rem",
      },
    },
  },
  plugins: [],
};


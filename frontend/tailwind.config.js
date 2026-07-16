/** @type {import('tailwindcss').Config} */

// Tailwind CSS configuration — defines which files to scan for class
// names, plus custom brand colors, fonts, and a couple of small
// entrance animations used across the app.

module.exports = {

  // Only scan pages and components for Tailwind classes, to keep the build fast
  content: [

    "./pages/**/*.{js,ts,jsx,tsx}",

    "./components/**/*.{js,ts,jsx,tsx}"

  ],

  theme: {

    extend: {

      // Custom "techmart" brand color palette, usable as e.g. bg-techmart-blue
      colors: {

        techmart: {

          blue: "#0066FF",

          "blue-dark": "#004FCC",

          "blue-light": "#EBF2FF"

        }

      },

      // System font stack, matching the fonts used in globals.css
      fontFamily: {

        sans: [

          "-apple-system",

          "BlinkMacSystemFont",

          "Segoe UI",

          "Roboto",

          "Helvetica Neue",

          "Arial",

          "sans-serif"

        ]

      },

      // Named animation utilities, e.g. className="animate-fade-in"
      animation: {

        "fade-in": "fadeIn 0.3s ease-out",

        "slide-up": "slideUp 0.25s ease-out"

      },

      keyframes: {

        fadeIn: { from: { opacity: 0 }, to: { opacity: 1 } },

        slideUp: {

          from: { opacity: 0, transform: "translateY(10px)" },

          to: { opacity: 1, transform: "translateY(0)" }

        }

      }

    }

  },

  plugins: []

};

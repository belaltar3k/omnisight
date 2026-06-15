/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,ts}",
  ],
  theme: {
    extend: {

      /* ── Widths ─────────────────────────────────────────────────────────── */
      width: {
        'sidebar':           '220px',
        'sidebar-collapsed': '3.5rem',
      },

      /* ── Colors ─────────────────────────────────────────────────────────── */
      colors: {

        /* Primitives */
        'void':         '#080d18',
        'surface-base': '#0b0f1a',
        'surface-well': '#0b1020',
        'surface-dark': '#0c1a3a',
        'panel':        '#0d1525',
        'panel-alt':    '#0d2040',

        /* Borders */
        'border-subtle': '#1a2235',
        'border-mid':    '#1e293b',
        'border-strong': '#1e3a5f',
        'border-accent': '#2a3555',
        'border-deep':   '#334155',

        /* Text */
        'text-primary':   '#ffffff',
        'text-secondary': '#94a3b8',
        'text-muted':     '#64748b',
        'text-faint':     '#334155',

        /* Brand */
        'brand':      '#3b82f6',
        'brand-dark': '#1e3a5f',
        'brand-deep': '#0d2040',

        /* Status */
        'success':      '#22c55e',
        'success-bg':   '#065f46',
        'success-deep': '#166534',

        'warning':      '#fef08a',
        'warning-bg':   '#78350f',
        'warning-mid':  '#713f12',
        'warning-deep': '#451a03',

        'danger':      '#ef4444',
        'danger-mid':  '#dc2626',
        'danger-dark': '#b91c1c',
        'danger-deep': '#7f1d1d',

        /* Legacy aliases kept for backward compat */
        'cam-bg':       '#0b0f1a',
        'sidebar-bg':   '#080d18',
        'sidebar-border': '#1a2235',
        'panel-border': '#1a2235',
      },

      /* ── Spacing ─────────────────────────────────────────────────────────── */
      spacing: {
        '13': '3.25rem',
        '15': '3.75rem',
        '18': '4.5rem',
        '22': '5.5rem',
      },

      /* ── Border radius ───────────────────────────────────────────────────── */
      borderRadius: {
        'sm2': '0.375rem',
        'xl2': '1rem',
      },

      /* ── Font families ───────────────────────────────────────────────────── */
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'ui-monospace', 'monospace'],
      },

      /* ── Font sizes ──────────────────────────────────────────────────────── */
      fontSize: {
        '2xs': ['0.625rem', { lineHeight: '1rem' }],
      },

      /* ── Animations ──────────────────────────────────────────────────────── */
      animation: {
        'pulse-slow': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in':    'fadeIn 200ms ease forwards',
        'slide-in':   'slideIn 200ms ease forwards',
      },

      keyframes: {
        fadeIn: {
          from: { opacity: '0' },
          to:   { opacity: '1' },
        },
        slideIn: {
          from: { opacity: '0', transform: 'translateY(-6px)' },
          to:   { opacity: '1', transform: 'translateY(0)' },
        },
      },

      /* ── Box shadows ─────────────────────────────────────────────────────── */
      boxShadow: {
        'card':   '0 1px 3px rgba(0,0,0,0.5)',
        'focus':  '0 0 0 2px rgba(59,130,246,0.40)',
        'brand':  '0 4px 12px rgba(59,130,246,0.20)',
      },
    },
  },
  plugins: [],
};

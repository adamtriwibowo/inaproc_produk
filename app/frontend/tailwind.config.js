/** Token dari design system (ui-ux-pro-max): merah INAPROC, sidebar terang, Plus Jakarta Sans + JetBrains Mono. */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        primary: 'rgb(var(--primary) / <alpha-value>)',
        'on-primary': 'rgb(var(--on-primary) / <alpha-value>)',
        'primary-dark': 'rgb(var(--primary-dark) / <alpha-value>)',
        accent: 'rgb(var(--accent) / <alpha-value>)',
        side: 'rgb(var(--side) / <alpha-value>)',
        bg: 'rgb(var(--bg) / <alpha-value>)',
        card: 'rgb(var(--card) / <alpha-value>)',
        fg: 'rgb(var(--fg) / <alpha-value>)',
        muted: 'rgb(var(--muted) / <alpha-value>)',
        'muted-fg': 'rgb(var(--muted-fg) / <alpha-value>)',
        line: 'rgb(var(--line) / <alpha-value>)',
        ok: 'rgb(var(--ok) / <alpha-value>)',
        'ok-bg': 'rgb(var(--ok-bg) / <alpha-value>)',
        warn: 'rgb(var(--warn) / <alpha-value>)',
        'warn-bg': 'rgb(var(--warn-bg) / <alpha-value>)',
        info: 'rgb(var(--info) / <alpha-value>)',
        'info-bg': 'rgb(var(--info-bg) / <alpha-value>)',
        bad: 'rgb(var(--bad) / <alpha-value>)',
        'bad-bg': 'rgb(var(--bad-bg) / <alpha-value>)',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}

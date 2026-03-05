# Budget Bo Frontend

Frontend Next.js 14 pour le SaaS Spending Tracker.

## Stack

- **Next.js 14** (App Router)
- **TypeScript**
- **Tailwind CSS**
- **shadcn/ui** (composants UI)
- **Tremor.so** (dashboards/data viz)

## Développement

```bash
# Installation
npm install

# Dev server
npm run dev

# Build
npm run build
```

## Structure

```
app/
├── page.tsx           # Dashboard
├── transactions/      # Page transactions
├── recurring/         # Page dépenses récurrentes
├── login/             # Page login
├── layout.tsx         # Root layout
├── globals.css        # Styles globaux
└── dashboard-layout.tsx # Layout avec sidebar

components/
├── ui/                # Composants shadcn/ui
└── sidebar.tsx        # Navigation

lib/
└── utils.ts           # Utilities (cn function)
```

## Intégration Backend

Le frontend communique avec le backend FastAPI via le reverse proxy Next.js.

- API URL: `/api/*` → `http://backend:8000/*`
- Auth: Sessions via cookies HttpOnly

# Budget Bo Frontend

Interface web Next.js connectée au backend Django.

## Stack

- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS
- shadcn/ui
- TanStack Query

## Pages principales

- `/login` : entrée OAuth Google
- `/` : dashboard (KPIs, catégories, transactions récentes)
- `/transactions` : liste paginée + filtres + édition catégorie
- `/transactions/[id]` : détail transaction
- `/credentials` : gestion des comptes bancaires et sync
- `/recurring` : dépenses récurrentes et détection manuelle

## Développement

```bash
npm install
npm run dev
```

Frontend local: `http://localhost:3000`

## Configuration

Variable utile:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

En dev, les appels peuvent aussi passer via le middleware/proxy Next.js (`/api/*`).

## Vérification rapide

```bash
npm run build
```

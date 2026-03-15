# Guide Google OAuth (Django + allauth)

## Pré-requis

- Un projet Google Cloud
- OAuth Client ID de type **Web application**
- Backend accessible sur `http://localhost:8000`
- Frontend accessible sur `http://localhost:3000`

## Configuration Google Cloud

Dans **APIs & Services > Credentials**:

- **Authorized JavaScript origins**
  - `http://localhost:8000`
- **Authorized redirect URIs**
  - `http://localhost:8000/auth/social/google/login/callback/`

> Le login démarre via `/auth/login`, puis allauth prend le relais.

## Variables d'environnement backend

```env
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
FRONTEND_URL=http://localhost:3000
# Production only - Force HTTPS in OAuth callbacks
OAUTH_BASE_URL=https://budget.victorsmits.com
```

## Flux de connexion

1. Le frontend redirige vers `/api/auth/login`.
2. Le backend déclenche la redirection Google (`/auth/social/google/login/`).
3. Après callback Google, allauth termine l'authentification.
4. L'utilisateur revient côté frontend (`FRONTEND_URL`).
5. Les endpoints `GET /auth/me` et `GET /users/me` valident la session.

## Endpoints utiles

- `GET /auth/login`
- `GET /auth/callback`
- `POST /auth/logout`
- `GET /auth/me`
- `GET /users/me`
- `POST /authtest-login` (dev uniquement)

## Dépannage

### `redirect_uri_mismatch`

Vérifie l'URI exacte déclarée dans Google Cloud:
- En dev: `http://localhost:8000/auth/social/google/login/callback/`
- En prod: `https://budget.victorsmits.com/auth/social/google/login/callback/`

### Callback HTTP en production

Si le callback est en HTTP au lieu de HTTPS:
1. Ajoutez `OAUTH_BASE_URL=https://budget.victorsmits.com` dans votre `.env`
2. Redémarrez le backend
3. Mettez à jour l'URI autorisée dans Google Cloud

### `Google OAuth is not configured` (503)

`GOOGLE_CLIENT_ID` et/ou `GOOGLE_CLIENT_SECRET` manquants dans l'environnement backend.

### Session non persistée côté frontend

- Vérifier `FRONTEND_URL` côté backend.
- Vérifier l'usage de cookies (credentials inclus côté frontend).
- Vérifier que l'URL API frontend pointe bien vers le backend (`NEXT_PUBLIC_API_URL` / proxy Next).

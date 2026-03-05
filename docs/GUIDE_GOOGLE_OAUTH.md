# Guide : Configuration Google OAuth pour Budget Bo

## Étape 1 : Créer un projet Google Cloud

1. Allez sur https://console.cloud.google.com
2. Cliquez sur le sélecteur de projet (en haut) → "New Project"
3. Nommez-le : `Budget Bo Auth`
4. Cliquez "Create"

## Étape 2 : Activer l'API Google OAuth

1. Dans le menu (☰), allez sur **"APIs & Services" > "OAuth consent screen"**
2. Sélectionnez **"External"** (pour tester avec n'importe quel compte Gmail)
3. Cliquez "Create"

## Étape 3 : Configurer l'écran de consentement

Remplissez les champs obligatoires :
- **App name** : `Budget Bo`
- **User support email** : votre email
- **Developer contact information** : votre email
- Cliquez "Save and Continue" jusqu'à la fin

## Étape 4 : Créer les credentials OAuth 2.0

1. Allez sur **"APIs & Services" > "Credentials"**
2. Cliquez **"Create Credentials" > "OAuth client ID"**
3. Application type : **"Web application"**
4. **Name** : `Budget Bo Web Client`
5. **Authorized redirect URIs** (très important !) :
   ```
   http://localhost:8000/auth/callback
   ```
6. Cliquez "Create"

## Étape 5 : Récupérer les clés

Une fenêtre popup apparaît avec :
- **Client ID** (ex: `123456789-abc123def456.apps.googleusercontent.com`)
- **Client Secret** (ex: `GOCSPX-xxxxxxxxxxxxxxxxx`)

⚠️ **Copiez-les immédiatement** - le secret ne sera plus visible après !

## Étape 6 : Configurer Budget Bo

Dans le fichier `.env` du projet :

```bash
# Éditer le fichier
nano /home/victor-smits/workspace/budget-bo/.env
```

Remplacez les placeholders :
```env
GOOGLE_CLIENT_ID=123456789-abc123def456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxxxxx
```

## Étape 7 : Redémarrer l'application

```bash
cd /home/victor-smits/workspace/budget-bo
docker compose up -d
```

## Étape 8 : Tester

Ouvrez votre navigateur :
```
http://localhost:8000/auth/login
```

Vous devriez être redirigé vers Google pour l'authentification !

---

## 🔧 Problèmes courants

### "redirect_uri_mismatch"
L'URI dans le fichier `.env` doit être **exactement** celui configuré dans Google Cloud.

### "access_denied"
Votre compte email doit être ajouté comme "Test user" dans :
Google Cloud Console → OAuth consent screen → Test users

### La connexion ne persiste pas
Vérifiez que le cookie est bien créé avec `HttpOnly` et `SameSite=Lax`

---

## 📋 Récapitulatif des URLs importantes

| URL | Description |
|-----|-------------|
| http://localhost:8000/auth/login | Lance le login Google |
| http://localhost:8000/auth/callback | Callback OAuth (configuré dans Google) |
| http://localhost:8000/auth/me | Voir l'utilisateur connecté |
| http://localhost:8000/auth/logout | Déconnexion |
| http://localhost:8000/docs | Documentation API |

---

## 🎨 Optionnel : Personnaliser l'écran de consentement

Vous pouvez ajouter :
- Logo de l'application (URL publique)
- Liens vers votre politique de confidentialité
- Page d'accueil

Cela rend l'écran de consentement Google plus professionnel.

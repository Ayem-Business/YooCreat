# 🔐 Guide d'Utilisation - Authentification Google OAuth (YooCreat)

## ✅ Fonctionnalité Implémentée

L'authentification Google via Emergent OAuth est maintenant **entièrement fonctionnelle** dans YooCreat.

## 🚀 Comment Tester la Connexion Google

### Méthode 1 : Test Manuel dans le Navigateur

1. **Ouvrez l'application** : 
   - Allez sur `http://localhost:3000` (ou votre URL de déploiement)

2. **Cliquez sur "Continuer avec Google"** :
   - Le bouton vous redirigera vers la page d'authentification Emergent
   - Vous serez invité à vous connecter avec votre compte Google

3. **Autorisez l'application** :
   - Connectez-vous avec votre compte Google
   - Acceptez les permissions

4. **Redirection automatique** :
   - Vous serez redirigé vers votre Dashboard YooCreat
   - Votre compte sera automatiquement créé (si nouveau) ou connecté (si existant)
   - Vos informations (nom, email, photo) seront synchronisées

## 🔧 Comment Fonctionne le Flow OAuth

### Backend (`/app/backend/server.py`)

1. **Route `/api/auth/google`** :
   - Reçoit le `session_id` depuis le frontend
   - Échange le `session_id` contre les données utilisateur via l'API Emergent
   - Crée ou récupère l'utilisateur dans MongoDB
   - Stocke la session (valide 7 jours)
   - Retourne un cookie httpOnly sécurisé

2. **Authentication Middleware** :
   - Supporte **deux méthodes** d'authentification :
     - Cookie `session_token` (Google OAuth)
     - Header `Authorization: Bearer <jwt_token>` (Email/Password)

3. **Route `/api/auth/logout`** :
   - Supprime la session de la base de données
   - Efface le cookie

### Frontend (`/app/frontend/src/App.js`)

1. **Bouton "Continuer avec Google"** :
   - Redirige vers `https://auth.emergentagent.com/?redirect=<dashboard_url>`

2. **Callback OAuth** :
   - L'utilisateur revient avec `#session_id=...` dans l'URL
   - Le frontend détecte automatiquement le `session_id`
   - Appelle `/api/auth/google` pour échanger le session_id
   - Stocke les données utilisateur et le cookie

3. **Axios Configuration** :
   - `axios.defaults.withCredentials = true` pour envoyer les cookies automatiquement
   - Support des deux modes d'auth (cookie + JWT)

## 📊 Base de Données

### Collection `users`
```javascript
{
  _id: "user_1760777xxx",
  username: "Jean Dupont",
  email: "jean@gmail.com",
  password_hash: null, // null pour OAuth users
  google_id: "google_id_xxx",
  picture: "https://lh3.googleusercontent.com/...",
  created_at: "2025-10-18T09:00:00Z"
}
```

### Collection `user_sessions`
```javascript
{
  user_id: "user_1760777xxx",
  session_token: "eyJhbGci...",
  expires_at: ISODate("2025-10-25T09:00:00Z"), // 7 jours
  created_at: ISODate("2025-10-18T09:00:00Z")
}
```

## 🔍 Vérification

### 1. Vérifier que le backend fonctionne
```bash
curl http://localhost:8001/api/health
# Devrait retourner: {"status": "ok", "service": "YooCreat API"}
```

### 2. Vérifier la base de données après connexion Google
```bash
mongosh --eval "use yoocreat; db.users.find({google_id: {\$exists: true}}).pretty();"
mongosh --eval "use yoocreat; db.user_sessions.find().pretty();"
```

### 3. Tester l'endpoint d'authentification avec un token
```bash
# Remplacez SESSION_TOKEN par un vrai token depuis la DB
curl -X GET http://localhost:8001/api/auth/me \
  -H "Authorization: Bearer SESSION_TOKEN"
```

## ⚠️ Points Importants

### Sécurité
- ✅ Cookies httpOnly (protection XSS)
- ✅ Session expiration (7 jours)
- ✅ Validation des tokens
- ✅ CORS configuré
- ⚠️ En production : activez `secure=True` pour HTTPS

### Multi-Authentification
L'application supporte **deux modes** simultanément :
- **Email/Password** → JWT Token stocké dans localStorage
- **Google OAuth** → Session Token stocké dans cookie httpOnly

Un utilisateur peut :
1. S'inscrire par email puis se connecter avec Google (même email)
2. S'inscrire avec Google puis utiliser email/password (après reset password)

## 🐛 Dépannage

### Le bouton Google ne redirige pas
- Vérifiez que le frontend est accessible
- Ouvrez la console navigateur (F12) pour voir les erreurs

### Session_id non reçu après OAuth
- Vérifiez l'URL de redirection dans le code
- La redirection doit pointer vers `/dashboard` pas `/`

### Erreur "Invalid session ID"
- Le session_id expire rapidement (quelques minutes)
- Ne pas rafraîchir la page pendant le processus OAuth

### Cookie non envoyé dans les requêtes
- Vérifiez `axios.defaults.withCredentials = true`
- Vérifiez les paramètres CORS du backend
- En dev local, `secure=False` et `samesite=lax`

## 📝 Tests Recommandés

### Test 1 : Nouveau compte Google
1. Utilisez un compte Google jamais utilisé sur YooCreat
2. Cliquez "Continuer avec Google"
3. Vérifiez que le compte est créé dans la DB
4. Vérifiez l'accès au Dashboard

### Test 2 : Compte existant
1. Créez un compte via Email/Password
2. Déconnectez-vous
3. Connectez-vous avec Google (même email)
4. Vérifiez que c'est le même compte (pas de doublon)

### Test 3 : Persistance
1. Connectez-vous avec Google
2. Fermez le navigateur
3. Rouvrez et allez sur l'application
4. Vous devez être toujours connecté (cookie valide 7 jours)

### Test 4 : Déconnexion
1. Connecté avec Google
2. Cliquez "Déconnexion"
3. Vérifiez que la session est supprimée de la DB
4. Vérifiez que vous êtes redirigé vers la page de connexion

## 🎉 Résultat Attendu

Après connexion Google réussie :
- ✅ Photo de profil visible dans le Dashboard
- ✅ Nom d'utilisateur affiché
- ✅ Email synchronisé
- ✅ Accès à toutes les fonctionnalités (création d'ebooks, etc.)
- ✅ Session persistante (pas besoin de se reconnecter)

## 📧 Support

Si vous rencontrez des problèmes :
1. Vérifiez les logs backend : `/var/log/supervisor/backend.err.log`
2. Vérifiez les logs frontend : Console navigateur (F12)
3. Vérifiez la base de données MongoDB
4. Contactez le support technique

---

**Version** : 1.0  
**Date** : 18 octobre 2025  
**Application** : YooCreat  
**Authentification** : Emergent OAuth (Google)

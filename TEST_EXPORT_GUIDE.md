# 🧪 Guide de Test - Export et Couverture IA

## 📋 Fonctionnalités à Tester

### 1. Export Multi-Formats
### 2. Génération de Couverture par IA

---

## 🎯 Scénario de Test Complet

### Étape 1 : Créer un Ebook Complet

1. **Connexion**
   - Allez sur http://localhost:3000 (ou votre URL de déploiement)
   - Connectez-vous ou inscrivez-vous

2. **Créer un Nouvel Ebook**
   - Cliquez sur "Créer un Ebook"
   - Remplissez le formulaire :
     - **Nom auteur** : Votre nom
     - **Titre** : "Guide de Test Export"
     - **Ton** : Professionnel
     - **Public** : Adultes, Débutants
     - **Description** : "Un ebook de test pour valider les fonctionnalités d'export"
     - **Nombre chapitres** : 3
     - **Longueur** : Court: 5-10 pages

3. **Générer la Table des Matières**
   - Cliquez sur "Générer la table des matières"
   - Attendez 5-10 secondes
   - **Vérifier** : Vous devez voir Introduction + 3 chapitres + Conclusion (5 éléments au total)

4. **Générer le Contenu**
   - Cliquez sur "Générer le contenu complet"
   - Attendez 30-60 secondes (génération de 5 chapitres)
   - **Vérifier** : Vous devez voir le contenu de tous les chapitres

5. **Aller au Dashboard**
   - Cliquez sur "Voir mes Ebooks"
   - **Vérifier** : Votre ebook "Guide de Test Export" apparaît dans la liste

6. **Ouvrir l'Ebook**
   - Cliquez sur la carte de l'ebook
   - **Vérifier** : Vous arrivez sur la page de visualisation

---

## 🎨 Test 1 : Génération de Couverture IA

### Objectif
Tester la génération automatique du design de couverture par l'IA.

### Actions

1. **Sur la page de visualisation de l'ebook**
   - En haut à droite, vous devez voir le bouton "🎨 Générer Couverture"

2. **Cliquer sur "Générer Couverture"**
   - Le bouton affiche "Génération..." avec un spinner
   - Attendez 5-10 secondes

3. **Vérifier la Couverture Générée**
   - Une nouvelle section "📐 Design de Couverture" apparaît
   - Le bouton devient "✅ Couverture OK" (vert)

### Ce qui doit être affiché

**Section Couverture** :
- ✅ **Visuel de la couverture** (à gauche)
  - Fond avec gradient de couleurs
  - Titre de l'ebook en grand
  - Nom de l'auteur
  - Sous-titre/tagline (si généré)

- ✅ **Détails du design** (à droite)
  - **Palette de couleurs** : 3-4 carrés de couleur (codes HEX)
  - **Style** : Description du style graphique
  - **Accroche** : Phrase percutante
  - **Typographie** : Police recommandée avec notes

- ✅ **Texte de dos de couverture** (en bas)
  - 2-3 phrases décrivant le livre

### Critères de Réussite

- [ ] Bouton cliquable et réactif
- [ ] Génération en ~5-10 secondes
- [ ] Affichage de la section couverture
- [ ] Gradient de couleurs visible
- [ ] Toutes les informations présentes
- [ ] Design cohérent avec les couleurs YooCreat

### En cas d'erreur

**Si "Erreur lors de la génération"** :
- Vérifiez les logs backend : `tail -f /var/log/supervisor/backend.err.log`
- Vérifiez que l'ebook existe et a du contenu
- Testez l'API : `curl -X POST http://localhost:8001/api/ebooks/generate-cover -H "Authorization: Bearer TOKEN" -d '"ebook_id"'`

---

## 📤 Test 2 : Export Multi-Formats

### Objectif
Tester le téléchargement de l'ebook dans les 5 formats disponibles.

### Actions Préliminaires

**Sur la page de visualisation de l'ebook**
- En haut à droite, vous devez voir le bouton "📤 Exporter"

### Test 2.1 : Export PDF

1. **Cliquer sur "Exporter"**
   - Un menu déroulant s'ouvre avec 5 options

2. **Sélectionner "📄 PDF - Impression professionnelle"**
   - Le navigateur télécharge automatiquement un fichier `.pdf`

3. **Ouvrir le fichier PDF**
   - **Page de couverture** : Titre + Auteur avec couleurs
   - **Table des matières** : Liste des chapitres
   - **Chapitres** : Contenu avec pagination
   - **Sous-titres** : ##Titres bien formatés

**Critères de Réussite PDF** :
- [ ] Téléchargement automatique
- [ ] Nom de fichier : `Guide_de_Test_Export.pdf`
- [ ] Page de couverture présente
- [ ] Table des matières cliquable
- [ ] Chapitres bien séparés (saut de page)
- [ ] Couleurs YooCreat (bleu, violet, orange)
- [ ] Texte justifié et lisible

### Test 2.2 : Export EPUB

1. **Cliquer sur "Exporter" → "📖 EPUB - Liseuses électroniques"**
   - Téléchargement d'un fichier `.epub`

2. **Ouvrir avec une application EPUB**
   - Calibre (PC/Mac)
   - Apple Books (Mac/iOS)
   - Google Play Books (Android)
   - Extension navigateur (EPUBReader)

3. **Vérifier**
   - Navigation par chapitres
   - Table des matières fonctionnelle
   - Texte adaptable (zoom)
   - Métadonnées (titre, auteur)

**Critères de Réussite EPUB** :
- [ ] Téléchargement OK
- [ ] Extension `.epub`
- [ ] Ouverture dans lecteur EPUB
- [ ] Navigation par chapitres
- [ ] CSS appliqué (couleurs, styles)
- [ ] Métadonnées correctes

### Test 2.3 : Export HTML (Flipbook)

1. **Cliquer sur "Exporter" → "🌐 HTML - Flipbook interactif"**
   - Téléchargement d'un fichier `.html`

2. **Ouvrir le fichier HTML dans un navigateur**
   - Double-clic sur le fichier téléchargé

3. **Tester l'Interactivité**
   - **Page de couverture** avec gradient animé
   - **Bouton "Suivant"** → Va à la table des matières
   - **Clic sur entrée TOC** → Va au chapitre correspondant
   - **Boutons Précédent/Suivant** fonctionnels
   - **Indicateur de page** (ex: 3 / 7)
   - **Navigation clavier** : ← et → fonctionnelles

**Critères de Réussite HTML** :
- [ ] Fichier HTML autonome (pas de dépendances)
- [ ] Page de couverture avec gradient bleu-violet
- [ ] Table des matières cliquable
- [ ] Navigation par boutons fonctionnelle
- [ ] Navigation clavier (flèches) fonctionnelle
- [ ] Indicateur de page dynamique
- [ ] Design responsive
- [ ] Animations fluides

### Test 2.4 : Export DOCX

1. **Cliquer sur "Exporter" → "📝 DOCX - Édition Word"**
   - Téléchargement d'un fichier `.docx`

2. **Ouvrir avec Microsoft Word ou LibreOffice**

3. **Vérifier l'Édition**
   - **Éditable** : Modifier le texte
   - **Styles** : Heading 1, Heading 2 appliqués
   - **Couleurs** : Titres en bleu/violet
   - **Table des matières** : Numérotée
   - **Sauts de page** entre chapitres

**Critères de Réussite DOCX** :
- [ ] Ouverture dans Word/LibreOffice
- [ ] Texte 100% éditable
- [ ] Styles de paragraphes préservés
- [ ] Couleurs personnalisées visibles
- [ ] Structure hiérarchique correcte
- [ ] Table des matières présente

### Test 2.5 : Export MOBI (Kindle)

1. **Cliquer sur "Exporter" → "📚 MOBI - Kindle"**
   - Téléchargement d'un fichier `.epub` (optimisé Kindle)

2. **Options de Test**
   - **Option A** : Envoyer à votre email Kindle (@kindle.com)
   - **Option B** : Convertir avec Calibre : `ebook-convert fichier.epub fichier.mobi`
   - **Option C** : Lire directement sur Kindle récent (support EPUB)

**Critères de Réussite MOBI** :
- [ ] Téléchargement du fichier EPUB
- [ ] Note dans les headers sur la conversion
- [ ] Compatible avec envoi email Kindle
- [ ] Ou convertible avec Calibre

---

## 🎭 Scénarios de Test Avancés

### Scénario A : Test avec Ebook Long

1. Créer un ebook avec 10 chapitres
2. Générer contenu complet
3. Générer couverture
4. Exporter en PDF
5. **Vérifier** : Pagination correcte, pas de débordement

### Scénario B : Test Multi-Export

1. Sur le même ebook, exporter successivement tous les formats
2. **Vérifier** : Aucune erreur, tous les téléchargements réussis
3. **Comparer** : Contenu identique dans tous les formats

### Scénario C : Test Sans Couverture

1. Créer un ebook, ne pas générer la couverture
2. Exporter en PDF
3. **Vérifier** : Export fonctionne quand même (page de couverture simple)

### Scénario D : Régénération de Couverture

1. Générer une couverture
2. Cliquer à nouveau sur "Générer Couverture"
3. **Vérifier** : Nouvelle couverture générée (différente)
4. **Vérifier** : L'ancienne est remplacée

---

## 🐛 Problèmes Potentiels et Solutions

### Erreur : "Erreur lors de l'export"

**Causes possibles** :
- Ebook n'a pas de contenu généré
- Problème d'authentification (token expiré)
- Backend non accessible

**Solution** :
```bash
# Vérifier le backend
curl -s http://localhost:8001/api/health

# Vérifier l'ebook
curl -X GET "http://localhost:8001/api/ebooks/EBOOK_ID" \
  -H "Authorization: Bearer TOKEN"

# Vérifier les logs
tail -f /var/log/supervisor/backend.err.log
```

### Erreur : Menu d'export ne s'ouvre pas

**Cause** : État React non mis à jour

**Solution** :
- Rafraîchir la page (F5)
- Vérifier console navigateur (F12)

### Erreur : Couverture ne se génère pas

**Causes** :
- Clé Emergent LLM expirée/invalide
- Ebook sans description

**Solution** :
```bash
# Tester l'API directement
curl -X POST http://localhost:8001/api/ebooks/generate-cover \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '"ebook_123"'
```

### Téléchargement ne démarre pas

**Cause** : Bloqueur de popup ou problème CORS

**Solution** :
- Autoriser les téléchargements depuis localhost
- Vérifier console pour erreurs CORS
- Tester en navigation privée

---

## ✅ Checklist Complète de Test

### Avant de Commencer
- [ ] Backend est en cours d'exécution
- [ ] Frontend est en cours d'exécution
- [ ] Compte utilisateur créé
- [ ] Au moins 1 ebook complet généré

### Tests Couverture IA
- [ ] Bouton "Générer Couverture" visible
- [ ] Génération réussie (5-10 sec)
- [ ] Section couverture affichée
- [ ] Visuel avec gradient
- [ ] Palette de couleurs (3-4 couleurs)
- [ ] Accroche présente
- [ ] Typographie recommandée
- [ ] Texte dos de couverture

### Tests Export
- [ ] Bouton "Exporter" visible
- [ ] Menu déroulant s'ouvre
- [ ] 5 options présentes

#### Export PDF
- [ ] Téléchargement automatique
- [ ] Fichier s'ouvre correctement
- [ ] Page de couverture
- [ ] Table des matières
- [ ] Chapitres paginés
- [ ] Couleurs correctes

#### Export EPUB
- [ ] Téléchargement OK
- [ ] Ouverture dans lecteur EPUB
- [ ] Navigation chapitres
- [ ] Métadonnées correctes

#### Export HTML
- [ ] Fichier HTML téléchargé
- [ ] Ouverture dans navigateur
- [ ] Flipbook interactif
- [ ] Navigation fonctionnelle
- [ ] Keyboard shortcuts (← →)

#### Export DOCX
- [ ] Téléchargement OK
- [ ] Ouverture Word/LibreOffice
- [ ] Entièrement éditable
- [ ] Styles préservés

#### Export MOBI
- [ ] EPUB téléchargé
- [ ] Envoyable à Kindle
- [ ] Ou convertible

---

## 📊 Résultats Attendus

À la fin des tests, vous devriez avoir :

✅ **1 ebook complet** avec contenu généré
✅ **1 couverture IA** avec design professionnel
✅ **5 fichiers exportés** dans différents formats
✅ **Tous les téléchargements** réussis
✅ **Tous les fichiers** ouverts et vérifiés

**Si tous les tests passent, les fonctionnalités sont prêtes pour la production !** 🎉

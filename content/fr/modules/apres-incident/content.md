# Que faire si vous avez été piégé ?

> **La plupart des brèches ne sont détectées qu'après 197 jours en moyenne.** (IBM Cost of a Data Breach 2023) Ce délai existe souvent parce que les victimes ne signalent pas. Votre réaction dans les premières minutes change tout.

## 🎯 Ce que vous apprendrez

- Connaître les actions exactes selon le type d'incident
- Comprendre pourquoi signaler vite est la bonne décision
- Savoir ce qu'il ne faut surtout pas faire

---

## Scénario réel

*Un commercial clique sur ce qu'il croit être une notification de signature électronique. Une page de connexion Microsoft s'ouvre. Il saisit ses identifiants. Puis rien — il pense à une erreur. Il attend. Il ne signale rien. Trois semaines plus tard, l'entreprise découvre que des emails avaient été transférés automatiquement vers une adresse externe depuis son compte — pendant trois semaines. Des offres commerciales confidentielles, des tarifs, des données clients. L'attaquant avait eu le temps de préparer une attaque ciblée contre un client de l'entreprise.*

Trente secondes de signalement auraient limité les dégâts à un seul identifiant compromis au lieu de trois semaines de fuite.

---

## J'ai cliqué sur un lien suspect

Agissez dans la minute :

1. **Ne saisissez rien** — si une page s'est ouverte, fermez-la sans entrer aucune information
2. **Déconnectez du réseau** — débranchez le câble Ethernet et/ou désactivez le Wi-Fi
3. **Appelez votre IT immédiatement** — décrivez précisément ce qui s'est passé
4. **Ne redémarrez pas** — un redémarrage peut effacer des traces utiles à l'analyse forensique
5. **Notez l'heure, l'URL** si vous vous en souvenez — cela aide l'investigation

---

## J'ai saisi mon mot de passe sur un site suspect

1. **Changez immédiatement** votre mot de passe sur le vrai service — en y accédant directement, pas via le lien reçu
2. Si c'était votre **email professionnel** : changez-le en priorité, puis vérifiez que des règles de transfert automatique n'ont pas été créées à votre insu
3. **Activez la MFA** si ce n'est pas encore fait
4. **Consultez les connexions récentes** dans les paramètres de sécurité du compte compromis
5. **Signalez à votre IT** — même si vous avez déjà changé le mot de passe

---

## J'ai transmis des informations confidentielles

1. **Signalez immédiatement** à votre responsable et à votre IT — même si vous avez honte, même si c'était une erreur
2. **Identifiez précisément** ce qui a été transmis : captures d'écran, documents, données clients, identifiants ?
3. Si des **données personnelles de tiers** sont impliquées : votre DPO doit être informé dans les 72h (obligation RGPD)
4. Conservez les emails et preuves — ils seront nécessaires pour l'investigation

---

## Ce qu'il ne faut surtout pas faire

- ❌ Attendre "que ça se passe" — chaque heure compte
- ❌ Essayer de gérer seul sans informer l'IT
- ❌ Supprimer les emails suspects, les logs, les preuves
- ❌ Redémarrer l'ordinateur sans accord de l'IT
- ❌ Continuer à utiliser la machine compromise

---

## L'état d'esprit juste

Signaler un incident n'est pas un aveu de faiblesse — c'est une démonstration de responsabilité. Personne ne vous reprochera d'avoir signalé. Ce qu'on reproche, c'est le silence.

Les équipes IT sont formées pour gérer ces situations, pas pour juger les personnes qui les signalent. Plus vous signalez vite, plus les dégâts sont limités — pour vous et pour l'entreprise.

---

## Après l'incident : les étapes de l'IT

Pour que vous compreniez pourquoi certaines demandes IT peuvent sembler contraignantes après un incident :

- **Analyse forensique** de votre machine — ne pas redémarrer preserve les traces
- **Revue des accès** depuis votre compte compromis
- **Notification CNIL** si des données personnelles sont concernées (72h)
- **Communication interne** pour alerter les collègues

---

## À retenir

- **Signaler vite = limiter les dégâts** — chaque minute compte
- **Ne redémarrez pas** sans validation IT — cela détruit des preuves
- Aucune action n'est à avoir honte si elle est signalée immédiatement
- La honte de signaler coûte bien plus cher que l'incident lui-même

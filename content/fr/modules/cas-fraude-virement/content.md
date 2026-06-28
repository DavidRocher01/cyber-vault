# Étude de cas : 3 millions perdus en 10 minutes

> **La fraude au virement (BEC — Business Email Compromise) a coûté 2,9 milliards de dollars aux entreprises mondiales en 2023. C'est la cybercriminalité la plus rentable au monde.** (FBI Internet Crime Report 2023)

## 🎯 Ce que vous apprendrez
- Comment fonctionne la fraude au virement, étape par étape
- Les signaux d'alerte que les victimes ont ignorés
- Les procédures simples qui auraient bloqué l'arnaque
- Votre rôle dans la prévention de ces fraudes

---

## L'entreprise

**Groupe Leblanc Industries** (nom fictif) : entreprise de taille intermédiaire, 280 employés, fournisseur du secteur aérospatial. Chiffre d'affaires : 45 millions d'euros.

---

## La chronologie

### Semaine J-3 : La préparation invisible

Les attaquants ont passé trois semaines à surveiller. Ils ont compromis la boîte email du directeur financier (DAF) via un phishing ciblé un mois plus tôt. Depuis, ils lisent tous ses emails sans rien modifier.

Ils savent que :
- L'entreprise traite régulièrement des virements importants avec un fournisseur italien (Ferretti Components)
- Le DAF est en déplacement professionnel à Dubaï du 12 au 17 mars
- La comptable principale, Isabelle Moreau, a pleins pouvoirs pour les virements en son absence

### Lundi 12 mars, 9h02 : L'email piégé

Isabelle reçoit un email du DAF :

> *"Isabelle, je suis en déplacement à Dubaï pour une opportunité d'acquisition confidentielle. Nous finalisons un accord et avons besoin d'un virement urgent de 2 980 000 € vers le compte suivant avant ce soir 17h. Je vous expliquerai tout à mon retour. C'est absolument CONFIDENTIEL — ne mentionnez cela à personne pour l'instant, pas même à Pierre [le PDG]. IBAN : FR76 3000 6000 0112 3456 7890 10. Comptez sur vous. Merci."*

L'email provient bien de l'adresse du DAF. La signature est identique. Le ton est celui qu'il utilise habituellement.

Isabelle est surprise, mais le DAF lui a déjà demandé de traiter des urgences en son absence.

### 9h15 : L'appel de confirmation

Isabelle tente de rappeler le DAF sur son mobile. Pas de réponse — il est "en réunion". Elle envoie un SMS. Pas de réponse immédiate.

Elle vérifie que l'IBAN est français et semble valide.

### 9h47 : Le virement est lancé

Isabelle effectue le virement depuis l'interface bancaire de l'entreprise. Le virement est validé automatiquement — elle a les pouvoirs nécessaires et le montant est dans ses limites habituelles (3 millions d'euros).

Elle envoie un email de confirmation au DAF.

### 11h20 : Le DAF rappelle

Le DAF, sorti de réunion, voit les appels d'Isabelle. Il la rappelle.

> — "Isabelle, j'ai vu tes appels. Tout va bien ?"
> — "Oui, j'ai traité le virement comme demandé."
> — "Quel virement ?"

**Silence.**

### 11h35 : La course contre la montre

L'entreprise appelle immédiatement sa banque. Le virement a déjà transité. La banque ouvre une procédure de rappel de fonds — mais l'argent a déjà été transféré vers un compte au Luxembourg, puis vers Hongkong.

**3 minutes.** C'est le temps qu'il faut aux cybercriminels pour vider un compte et transférer vers une juridiction hors d'atteinte.

Sur les 2,98 millions d'euros, **moins de 200 000 euros** seront récupérés après 18 mois de procédures judiciaires.

---

## Comment cela a-t-il été possible ?

### Vecteur 1 : La compromission de l'email du DAF
Les attaquants avaient accès à la boîte email depuis un mois. L'email d'Isabelle semblait authentique parce qu'il provenait réellement du compte du DAF.

**Signal d'alerte ignoré :** Le DAF avait reçu un email de phishing un mois plus tôt, qu'il avait simplement supprimé sans le signaler à l'IT.

### Vecteur 2 : L'urgence et la confidentialité comme pression
"Avant ce soir 17h" et "n'en parlez à personne" sont deux marqueurs classiques de la fraude. Ces injonctions visent à court-circuiter les procédures de contrôle.

**Signal d'alerte ignoré :** Isabelle a trouvé la demande inhabituelle mais a rationalisé : "Le DAF a ses raisons."

### Vecteur 3 : L'absence de vérification vocale directe
Isabelle a essayé d'appeler, mais n'a pas eu de réponse. Elle aurait dû attendre la confirmation vocale avant d'agir.

**Signal d'alerte ignoré :** Un SMS sans réponse n'est pas une confirmation. La règle absolue est : tout virement exceptionnel exige une confirmation vocale directe.

### Vecteur 4 : L'absence de double validation
Pour un virement de 3 millions d'euros, une seule validation (Isabelle) a suffi. Il n'y avait pas de second regard obligatoire.

**Ce qui aurait changé :** Une règle de double validation au-delà d'un certain montant (ex : 50 000 €) aurait bloqué le virement.

---

## Les 5 règles anti-fraude au virement

### 1. Toujours vérifier vocalement
Tout virement exceptionnel — même d'un montant habituel — demandé par email doit être confirmé par un appel téléphonique direct, sur un numéro connu (pas un numéro donné dans l'email).

> ❌ Virement reçu par email → Rappel sur le numéro dans l'email → Virement effectué
> ✅ Virement reçu par email → Rappel sur le numéro connu du carnet d'adresses → Confirmation vocale → Virement effectué

### 2. L'urgence est un signal d'alarme, pas une raison d'accélérer
Chaque fois qu'un email vous presse d'agir vite et en secret, ralentissez. Les fraudeurs créent une fausse urgence pour vous empêcher de réfléchir et de vérifier.

### 3. La confidentialité demandée = arrêt immédiat
"N'en parlez à personne" est un signal quasi-certain de fraude. Une vraie transaction légitime ne vous demandera jamais de contourner vos procédures internes.

### 4. Vérifier le RIB/IBAN indépendamment
Si un fournisseur habituel vous communique un nouveau RIB par email, vérifiez-le en appelant votre contact habituel chez ce fournisseur **sur un numéro que vous avez dans votre carnet d'adresses** — pas sur un numéro donné dans l'email.

### 5. Signaler toute tentative, même ratée
Si vous recevez un email de fraude et ne donnez pas suite — signalez-le quand même à votre IT et à votre responsable. Les attaquants réessaieront avec quelqu'un d'autre, ou affineront leur approche pour la prochaine tentative.

---

## Que faire si vous réalisez avoir été victime ?

**Chaque minute compte.** Agissez dans cet ordre :

1. **Appelez votre banque immédiatement** — la procédure de rappel de fonds a plus de chances de succès dans les premières heures
2. **Informez votre responsable et la direction** sans délai
3. **Préservez toutes les preuves** (emails, historiques d'appels)
4. **Déposez plainte** auprès de la police ou gendarmerie (nécessaire pour les assurances)
5. **Contactez Cybermalveillance.gouv.fr** pour être guidé

---

## Le profil type des victimes

Contrairement à l'idée reçue, les victimes ne sont pas naïves ou incompétentes. Ce sont souvent des professionnels expérimentés, consciencieux, qui pensent agir correctement.

Les attaquants choisissent soigneusement leur cible et leur moment : un dirigeant absent, un comptable sous pression, une période d'acquisition ou de fusion. Ils personnalisent chaque attaque avec des informations glanées sur LinkedIn, les sites web d'entreprise, les communiqués de presse.

**La défense n'est pas la méfiance — c'est la procédure.**

---

## Résumé — Vos 3 réflexes anti-fraude

1. **Virement exceptionnel = confirmation vocale obligatoire**, sur un numéro connu, sans exception
2. **Urgence + confidentialité = signal d'alarme**, pas une raison d'accélérer
3. **Nouveau RIB reçu par email = vérification indépendante** avant tout virement

Ces 10 secondes de vérification peuvent éviter des années de procédures.

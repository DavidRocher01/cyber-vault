# Continuité d'activité : votre rôle en cas de crise cyber

> **Le temps moyen pour reprendre une activité après un ransomware est de 22 jours. Avec un PCA testé, ce délai tombe à 4 jours.** (Coveware 2024)

## 🎯 Ce que vous apprendrez
- Ce qu'est un Plan de Continuité d'Activité (PCA) et pourquoi il vous concerne
- Votre rôle spécifique pendant et après une crise cyber
- Les réflexes qui permettent une reprise rapide

---

## Scénario réel

*Le lundi matin, les 120 employés d'une société de logistique arrivent au bureau pour trouver tous les ordinateurs chiffrés par un ransomware. Personne ne sait quoi faire. Les téléphones sont remplis de WhatsApps contradictoires. Certains redémarrent leurs machines (aggravant la propagation), d'autres appellent directement des clients pour les prévenir (avant que la direction ait eu le temps d'évaluer la situation). Résultat : 18 jours d'arrêt complet, perte de trois clients majeurs, et des données définitivement perdues faute de sauvegardes testées.*

Cette situation aurait été très différente si chaque employé avait su quoi faire — et surtout quoi ne pas faire — les premières heures.

---

## Qu'est-ce que la continuité d'activité ?

La **continuité d'activité** désigne la capacité d'une organisation à maintenir ou reprendre ses fonctions critiques après un incident grave — cyberattaque, incendie, panne électrique majeure, pandémie.

Le **Plan de Continuité d'Activité (PCA)** est le document qui décrit :
- Quelles fonctions sont critiques et doivent redémarrer en priorité
- Comment les reprendre en cas d'indisponibilité des systèmes habituels
- Qui décide quoi pendant la crise
- Comment communiquer en interne et en externe

Le **Plan de Reprise d'Activité (PRA)** est son complément technique : il décrit comment restaurer les systèmes informatiques.

---

## Ce que NIS2 exige

L'article 21 de NIS2 impose la **gestion de la continuité des activités** comme mesure obligatoire, incluant :

✅ Un PCA documenté et testé régulièrement
✅ Des sauvegardes régulières, chiffrées et testées
✅ Une procédure de gestion de crise activable rapidement
✅ Des exercices de simulation (au moins annuels)

---

## Les deux indicateurs clés : RTO et RPO

Votre IT et votre direction travaillent avec deux concepts fondamentaux :

**RTO — Recovery Time Objective** (Durée maximale d'interruption acceptable)
"Combien de temps pouvons-nous fonctionner sans ce système ?"
Exemple : notre CRM peut être indisponible 4 heures maximum.

**RPO — Recovery Point Objective** (Perte de données maximale acceptable)
"Jusqu'à quand remontons-nous les données en cas de restauration ?"
Exemple : nous pouvons perdre au maximum 1 heure de données.

Ces seuils définissent les priorités de reprise. En tant qu'employé, comprendre ces concepts vous aide à prioriser vos propres actions.

---

## Les 3 phases d'une crise cyber

### Phase 1 — Les premières heures : confinement

L'objectif est d'**arrêter la propagation**, pas de réparer.

**Ce que vous devez faire :**
- Signaler immédiatement tout comportement anormal (machine lente, fichiers chiffrés, messages de rançon)
- Suivre **scrupuleusement** les instructions de votre IT — même si elles vous semblent excessives
- Déconnecter votre machine du réseau si demandé (débrancher le câble, désactiver le Wi-Fi)
- **Ne pas redémarrer** votre machine sans instruction explicite de l'IT
- **Ne pas tenter de "réparer"** vous-même

**Ce que vous ne devez pas faire :**
❌ Partager des informations sur l'incident avec des personnes extérieures à l'organisation
❌ Publier quoi que ce soit sur les réseaux sociaux
❌ Contacter des clients ou partenaires sans instruction de la direction

### Phase 2 — Les premiers jours : modes dégradés

L'organisation fonctionne avec des moyens alternatifs pendant la restauration des systèmes.

**Modes dégradés typiques :**
- Utilisation de téléphones portables à la place des emails d'entreprise
- Communication par signal ou messagerie sécurisée alternative
- Processus manuels pour les opérations critiques (bons papier, validation téléphonique)
- Accès à des postes de travail de secours ou machines prêtées

**Votre rôle :** connaître à l'avance les procédures de mode dégradé de votre département. Demandez à votre manager de vous les présenter si ce n'est pas fait.

### Phase 3 — Les semaines suivantes : retour à la normale

La restauration progressive des systèmes, en commençant par les plus critiques.

**Votre vigilance reste importante :**
- Ne réintroduisez pas de données "sauvegardées" personnellement sans validation IT (clé USB, compte personnel, etc.) — elles pourraient être infectées
- Participez aux exercices de simulation post-incident si vous y êtes invité
- Remontez toute anomalie pendant la phase de reprise

---

## Les sauvegardes : la condition de la reprise

Sans sauvegardes valides, pas de reprise possible. La règle **3-2-1** (couverte dans le module dédié) s'applique.

**Ce que vous pouvez vérifier :**
- Avez-vous des données professionnelles uniquement sur votre disque local ? → Elles doivent être sur les serveurs de l'entreprise
- Utilisez-vous des plateformes non autorisées par votre IT pour stocker des données professionnelles ? → C'est du Shadow IT, et ces données ne seront pas couvertes par les sauvegardes entreprise

**Question à poser à votre IT :** "Si mon ordinateur tombe en panne demain, combien de temps pour récupérer toutes mes données ?"

---

## L'annuaire de crise : sachez qui appeler

En cas de crise, les systèmes habituels (email, téléphone IP, intranet) peuvent être indisponibles. Chaque employé doit connaître les contacts d'urgence hors système :

| Rôle | Information à connaître |
|------|------------------------|
| Votre manager direct | Son numéro de téléphone portable |
| Le responsable IT | Son numéro de portable |
| Le responsable sécurité (RSSI) | Son numéro de portable |
| L'astreinte IT | Le numéro d'astreinte si applicable |

Notez ces numéros sur papier — pas seulement dans votre téléphone professionnel qui pourrait être inaccessible.

---

## Résumé — Ce que vous devez retenir

| Phase | Votre rôle |
|-------|-----------|
| **Avant la crise** | Connaître les procédures de mode dégradé de votre département, noter les contacts d'urgence |
| **Premières heures** | Signaler, déconnecter si demandé, ne pas aggraver, ne pas communiquer |
| **Phase dégradée** | Appliquer les procédures alternatives, rester disponible, éviter le Shadow IT |
| **Reprise** | Ne réintroduire que des données validées, signaler toute anomalie |

La reprise après une cyberattaque dépend de chaque maillon de l'organisation. Votre comportement les premières heures peut faire la différence entre une reprise en 4 jours et une paralysie de 3 semaines.

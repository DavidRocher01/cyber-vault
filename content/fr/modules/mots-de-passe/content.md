# Créer et gérer des mots de passe solides

> **Les outils de crack modernes testent 10 milliards de combinaisons par seconde.** Un mot de passe de 8 caractères se craque en moins d'une heure. Un mot de passe de 16 caractères aléatoires : des millions d'années.

## 🎯 Ce que vous apprendrez

- Pourquoi vos anciens mots de passe ne suffisent plus
- Construire des mots de passe forts et mémorables
- Utiliser un gestionnaire pour en finir avec la réutilisation

---

## Scénario réel

*En 2022, des millions d'identifiants issus de fuites précédentes circulent sur des forums du dark web. Des attaquants les testent automatiquement sur des centaines de services — Gmail, LinkedIn, VPN d'entreprise, outils de comptabilité. Un employé qui utilise `Entreprise2020!` partout voit trois de ses comptes professionnels compromis en quelques heures, sans jamais avoir cliqué sur quoi que ce soit.*

C'est la **credential stuffing** — l'attaque la plus répandue et la plus silencieuse.

---

## Ce qui rend un mot de passe faible

Les outils d'attaque testent d'abord :

- Les 10 000 mots de passe les plus courants : `123456`, `password`, `azerty`, `motdepasse`
- Les mots du dictionnaire + substitutions : `p@ssw0rd`, `s3cur1ty`, `l3t5g0`
- Vos informations publiques : date de naissance, prénom, ville, équipe sportive
- Vos fuites passées — vérifiable sur [haveibeenpwned.com](https://haveibeenpwned.com)

Si un humain peut le deviner, une machine le trouvera en secondes.

---

## Les 3 règles fondamentales

**1. Long** — au moins 14 caractères, idéalement 16+

**2. Aléatoire** — aucun mot réel, aucun pattern, aucun sens humain

**3. Unique** — différent pour chaque compte, sans exception

---

## La technique de la phrase secrète

Impossible de mémoriser un mot de passe de 16 caractères aléatoires ? Construisez une phrase :

> `Café-Nuage-Bouton-47!` → 21 caractères, mémorable, robuste

Ou prenez les initiales d'une phrase personnelle :

> *"Mon premier vélo était rouge et j'avais 7 ans"*
> → `MpVéR&j'A7a!` → 12 caractères, complexe, mémorisable

---

## Pourquoi l'unicité est non-négociable

Si vous utilisez le même mot de passe sur 5 services et qu'un seul est piraté, l'attaquant teste immédiatement ce couple email/mot de passe partout ailleurs.

**24 milliards de couples email/mot de passe circulaient sur le dark web en 2023.** (Digital Shadows)

---

## Le gestionnaire de mots de passe

Retenir 60 mots de passe uniques est humainement impossible — c'est pour ça que les gestionnaires existent.

**Solutions reconnues :** KeePass (open source, local), Bitwarden (open source, cloud), 1Password, Dashlane.

Comment ça fonctionne :

- Un seul **mot de passe maître** très fort protège tout le reste
- Le gestionnaire génère des mots de passe aléatoires uniques pour chaque site
- Il remplit automatiquement les formulaires *et vérifie que l'URL correspond* — protection anti-phishing
- Il vous alerte si l'un de vos sites a été compromis

---

## Ce qu'il ne faut jamais faire

- ❌ Post-it collé à l'écran ou sous le clavier
- ❌ Fichier `mots-de-passe.xlsx` non chiffré
- ❌ Partager un mot de passe par email, SMS ou Teams
- ❌ Réutiliser le même partout "pour s'en souvenir"
- ❌ Incrémenter un chiffre (`Azerty2023!` → `Azerty2024!`)
- ❌ Communiquer votre mot de passe à quelqu'un qui le demande, même un prestataire IT

---

## À retenir

- **Long + Unique + Gestionnaire** — la combinaison gagnante
- Un gestionnaire de mots de passe n'est pas un luxe, c'est une nécessité
- Vérifiez vos fuites passées sur haveibeenpwned.com
- La MFA s'ajoute *en plus* — elle ne remplace pas un bon mot de passe

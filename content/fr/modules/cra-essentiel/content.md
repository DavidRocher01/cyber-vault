# Cyber Resilience Act : la sécurité des produits connectés

> **Le CRA imposera des exigences de cybersécurité à tous les produits numériques vendus en Europe. Estimation : 90 % des équipements connectés actuels ne seraient pas conformes.** (ENISA 2023)

## 🎯 Ce que vous apprendrez
- Pourquoi le CRA a été créé et quel problème il résout
- Qui est concerné et quelles sont les obligations
- Ce que cela change pour votre organisation
- Le calendrier de mise en conformité

---

## Le problème que le CRA résout

En 2023, il existait plus de 14 milliards d'appareils connectés en Europe. Des ampoules, des caméras de surveillance, des routeurs, des jouets pour enfants, des équipements industriels, des assistants vocaux... La grande majorité de ces appareils n'avaient aucune obligation de sécurité.

**Le résultat :** des millions d'appareils vulnérables, jamais mis à jour, utilisés comme relais dans des attaques massives. Le botnet Mirai (2016) a ainsi compromis des centaines de milliers de caméras IP mal sécurisées pour lancer l'une des plus grandes attaques DDoS de l'histoire.

Le Cyber Resilience Act (CRA) est le premier règlement européen à imposer des **obligations de sécurité aux fabricants** de produits numériques — pas seulement à leurs utilisateurs.

---

## Qu'est-ce que le CRA ?

Le CRA (Règlement européen 2024/2847) est entré en vigueur en décembre 2024. Il impose des exigences de cybersécurité à tous les **"produits comportant des éléments numériques"** vendus sur le marché européen.

---

## Qui est concerné ?

### Fabricants et développeurs
Tout fabricant ou développeur qui met sur le marché européen un produit "comportant des éléments numériques" est concerné :

- Fabricants d'équipements IoT (caméras, routeurs, thermostats, capteurs industriels)
- Éditeurs de logiciels commerciaux (applications, SaaS, OS)
- Développeurs d'applications mobiles
- Fabricants d'équipements réseau
- Vendeurs de solutions de cybersécurité

### Importateurs et distributeurs
Si vous importez ou distribuez des produits numériques d'un fabricant hors UE, vous pouvez hériter de certaines obligations de conformité.

---

## Les 3 catégories de produits

Le CRA classe les produits en 3 catégories selon leur criticité :

### Classe par défaut (90 % des produits)
Produits numériques sans fonction critique particulière : ampoules connectées, jouets, applications courantes.

**Obligations :** Auto-déclaration de conformité, documentation technique, support de sécurité.

### Classe I — Produits importants
Produits présentant un risque de sécurité plus élevé : navigateurs, gestionnaires de mots de passe, pare-feux, VPN, systèmes de contrôle industriels (ICS), microcontrôleurs.

**Obligations :** Audit par organisme tiers ou certification par schéma européen.

### Classe II — Produits critiques
Produits critiques pour l'infrastructure européenne : hyperviseurs, systèmes d'exploitation, composants de sécurité hardware.

**Obligations :** Certification obligatoire par organisme accrédité.

---

## Les obligations essentielles du CRA

### 1. Sécurité dès la conception (Security by Design)
Les produits doivent être conçus avec la sécurité intégrée dès le départ, pas ajoutée après coup :
- Pas de mots de passe par défaut identiques pour tous les appareils
- Surface d'attaque minimale (services non nécessaires désactivés par défaut)
- Authentification forte disponible
- Chiffrement des données sensibles

### 2. Gestion des vulnérabilités
Les fabricants doivent :
- Maintenir un inventaire des composants logiciels (SBOM — Software Bill of Materials)
- Publier des mises à jour de sécurité pendant toute la durée de vie du produit
- Notifier l'ENISA et les utilisateurs des vulnérabilités significatives dans les **24 heures**
- Proposer un canal de signalement des vulnérabilités (Coordinated Vulnerability Disclosure)

### 3. Documentation et transparence
- Déclaration de conformité CE avec mention de cybersécurité
- Documentation technique complète
- Instructions de sécurité pour l'utilisateur

### 4. Durée de support obligatoire
Pour la première fois, le CRA impose une durée minimale de support de sécurité. Les fabricants doivent fournir des mises à jour de sécurité pendant **au moins 5 ans** ou la durée de vie prévue du produit si elle est plus longue.

---

## Ce qui change pour les acheteurs

Le CRA profite aussi aux acheteurs de produits numériques — particuliers et organisations. Avec le CRA, vous pouvez vous attendre à :

- Le marquage CE sur les produits numériques intégrera des mentions de sécurité
- Les produits non conformes ne pourront plus être vendus en Europe
- Vous pourrez exiger des fabricants une durée de support de sécurité documentée
- Les notifications de vulnérabilités seront obligatoires

**Bonne pratique d'achat :** Demandez à vos fournisseurs leur SBOM (liste des composants logiciels) et la durée de support de sécurité garantie pour les équipements que vous achetez.

---

## Le calendrier de mise en conformité

| Date | Obligation |
|------|-----------|
| Décembre 2024 | Entrée en vigueur du règlement |
| Septembre 2026 | Obligations de notification des incidents et vulnérabilités |
| Décembre 2027 | **Pleine application** : tous les produits mis sur le marché doivent être conformes |

Les produits déjà sur le marché avant décembre 2027 ne sont pas immédiatement concernés, mais toute modification substantielle les soumet aux nouvelles règles.

---

## Les sanctions CRA

- Pour les non-conformités aux exigences essentielles : jusqu'à **15 millions d'euros** ou 2,5 % du CA mondial annuel
- Pour les fausses déclarations de conformité : jusqu'à **5 millions d'euros** ou 1 % du CA

---

## Différences CRA vs NIS2

| Aspect | NIS2 | CRA |
|--------|------|-----|
| Cible | Organisations utilisant des systèmes IT | Fabricants de produits numériques |
| Obligations | Sécurité organisationnelle | Sécurité des produits |
| Périmètre | Secteurs essentiels | Tout produit numérique vendu en UE |
| Durée de support | Non imposée | Minimum 5 ans |

NIS2 et CRA sont complémentaires : NIS2 protège les organisations, CRA protège les produits qu'elles utilisent.

---

## Résumé

Le CRA est une révolution dans la sécurité des produits numériques. Pour la première fois, les fabricants sont légalement responsables de la sécurité de leurs produits tout au long de leur cycle de vie.

**Si votre organisation fabrique ou distribue des produits numériques :** préparez votre conformité avant décembre 2027.

**Si votre organisation achète des produits numériques :** le CRA va progressivement améliorer la sécurité des équipements disponibles sur le marché européen. D'ici là, continuez à exiger des informations sur la sécurité et le support avant tout achat.

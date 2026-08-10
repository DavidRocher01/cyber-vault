/**
 * Rattrape la saisie faite AVANT que la page ne soit hydratee.
 *
 * LE DEFAUT, MESURE EN PRODUCTION LE 2026-08-09. Une page prerendue s'affiche
 * immediatement mais n'est pas encore interactive. Ce qui est tape pendant
 * cette fenetre est ecrit dans le DOM ; puis Angular hydrate le champ et y
 * ECRIT LA VALEUR DU `FormControl`, c'est-a-dire du vide. La saisie n'est donc
 * pas ignoree : elle est EFFACEE. Le formulaire reste invalide, son bouton
 * grise, et l'utilisateur voit ses champs se vider tout seuls.
 *
 * MESURE PRECISE, sur le build prerendu servi en statique. Un marqueur pose sur
 * le champ prerendu prouve qu'il n'est pas remplace :
 *
 *      0 ms  champ present, marqueur intact, valeur « MARQUEUR »
 *   1700 ms  champ present, marqueur INTACT, valeur « »
 *
 * 1700 ms, c'est la fin du loader de 1800 ms d'`AppComponent` : le contenu se
 * lie a ce moment-la, et l'ecriture du `FormControl` vide ecrase la frappe.
 *
 * CE QUI A ETE ESSAYE D'ABORD, ET N'A PAS MARCHE :
 *
 *   - `provideClientHydration(withEventReplay())`, la fonctionnalite d'Angular
 *     prevue pour rejouer les interactions pre-hydratation. Mesuree avec le
 *     harnais : les deux tests de saisie tombent exactement pareil ;
 *   - comparer `value` a `defaultValue` apres coup : inutile, puisque la valeur
 *     a deja ete effacee — les deux valent alors la chaine vide.
 *
 * D'OU CETTE APPROCHE : ENREGISTRER PENDANT, RESTAURER APRES. On ecoute la
 * frappe des le chargement du bundle, on retient ce qui a ete tape, et quand le
 * champ se vide tout seul on y remet la valeur puis on emet l'evenement natif
 * que le `ValueAccessor` d'Angular ecoute deja.
 *
 * ON NE TOUCHE A AUCUN ROUAGE INTERNE D'ANGULAR : ni `FormControl`, ni
 * injecteur d'element. Uniquement du DOM et des evenements natifs — ce qui rend
 * cette reprise indifferente aux versions.
 *
 * AUCUN COMPOSANT N'EST MODIFIE. Une correction qui demanderait d'importer une
 * directive dans chaque formulaire serait oubliee au premier ecran ajoute.
 */

/** Champs dont la valeur se lit dans `value`. */
type ChampTextuel = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;

/** Combien de temps surveiller l'effacement, en millisecondes.
 *
 *  Mesure a 1700 ms sur le build actuel ; on garde une marge large pour un
 *  reseau lent, puis on s'arrete — une surveillance sans fin serait une fuite. */
const DUREE_SURVEILLANCE_MS = 8000;
const PAS_MS = 100;

const TEXTUELS = 'input:not([type=checkbox]):not([type=radio]), textarea, select';

/**
 * Installe la reprise. A appeler AU PLUS TOT, avant le demarrage d'Angular :
 * tout ce qui est tape avant cet appel est hors de portee.
 *
 * @returns une fonction d'arret, pour les tests.
 */
export function installerRepriseSaisie(doc: Document, fenetre: Window): () => void {
  const saisi = new Map<ChampTextuel, string>();

  const noter = (e: Event) => {
    const cible = e.target as ChampTextuel | null;
    if (cible && typeof cible.value === 'string' && cible.matches?.(TEXTUELS)) {
      saisi.set(cible, cible.value);
    }
  };

  // En phase de CAPTURE : on veut voir la frappe meme si un gestionnaire
  // intermediaire arrete la propagation.
  doc.addEventListener('input', noter, true);

  // CE QUI A DEJA ETE TAPE AVANT CET APPEL, et c'est le cas le plus frequent :
  // le bundle pese pres d'un mega-octet, donc la page est visible bien avant
  // que cette ligne ne s'execute. Ecouter les frappes FUTURES ne suffisait pas —
  // le harnais l'a montre en echouant exactement comme avant.
  //
  // `defaultValue` reflete l'attribut ecrit par le serveur : un ecart signifie
  // une frappe, jamais un rendu. C'est ce qui evite de retenir — puis de
  // restaurer — une valeur que la page a legitimement pre-remplie.
  for (const champ of Array.from(doc.querySelectorAll<ChampTextuel>(TEXTUELS))) {
    if (champ instanceof HTMLSelectElement) continue;
    if (champ.value && champ.value !== champ.defaultValue) saisi.set(champ, champ.value);
  }

  let ecoule = 0;
  const minuteur = fenetre.setInterval(() => {
    ecoule += PAS_MS;

    for (const [champ, valeur] of saisi) {
      // Le champ a-t-il ete vide par l'hydratation ? On ne restaure que dans ce
      // sens : si l'utilisateur efface lui-meme, sa frappe est notee et les deux
      // valeurs restent egales.
      if (champ.value === valeur) continue;
      if (champ.value !== '') {
        saisi.delete(champ);
        continue;
      }

      champ.value = valeur;
      champ.dispatchEvent(new Event('input', { bubbles: true }));
      champ.dispatchEvent(new Event('change', { bubbles: true }));
      saisi.delete(champ);
    }

    // ON NE S'ARRETE PAS PARCE QUE LA LISTE EST VIDE. Une premiere version le
    // faisait, et se coupait au premier battement quand rien n'avait encore ete
    // tape — emportant l'ecouteur avec elle. Selon que la frappe precede ou suit
    // le demarrage du bundle, on perdait l'un ou l'autre cas ; le harnais
    // echouait pareil dans les deux, ce qui masquait la cause.
    if (ecoule >= DUREE_SURVEILLANCE_MS) arreter();
  }, PAS_MS);

  const arreter = () => {
    fenetre.clearInterval(minuteur);
    doc.removeEventListener('input', noter, true);
    saisi.clear();
  };

  return arreter;
}

import { bootstrapApplication } from '@angular/platform-browser';
import { isDevMode } from '@angular/core';
import * as Sentry from '@sentry/angular';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';
import { environment } from './environments/environment';
import { installerRepriseSaisie } from './app/core/reprise-saisie';

// AVANT TOUT LE RESTE, ET C'EST LE POINT. Une page prerendue s'affiche avant
// d'etre hydratee : le formulaire est visible mais mort, et ce qui y est tape
// sera efface quand Angular ecrira la valeur vide du `FormControl`. On note
// donc la frappe des maintenant, pour la remettre apres.
//
// Ici plutot que dans un composant : le moindre retard est de la saisie perdue,
// et `bootstrapApplication` ci-dessous ne demarre Angular qu'ensuite.
//
// Ici plutot qu'en ligne dans `index.html` : la CSP servie est
// `script-src 'self'`, un script en ligne exigerait d'autoriser son empreinte.
if (typeof window !== 'undefined') {
  installerRepriseSaisie(document, window);
}

// These browser-only initializations are skipped during SSR prerendering
if (typeof window !== 'undefined') {
  if (!isDevMode()) {
    Sentry.init({
      dsn: 'https://6ef59d099fc59577740218c655c25005@o4511257225986048.ingest.de.sentry.io/4511257233653840',
      environment: 'production',
      release: environment.version,
      tracesSampleRate: 0.1,
      sendDefaultPii: false,
    });
  }
}

if (typeof window !== 'undefined')
  console.log(
    '%c\n' +
      ' ██████╗██╗   ██╗██████╗ ███████╗██████╗ ███████╗ ██████╗ █████╗ ███╗   ██╗\n' +
      '██╔════╝╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗████╗  ██║\n' +
      '██║      ╚████╔╝ ██████╔╝█████╗  ██████╔╝███████╗██║     ███████║██╔██╗ ██║\n' +
      '██║       ╚██╔╝  ██╔══██╗██╔══╝  ██╔══██╗╚════██║██║     ██╔══██║██║╚██╗██║\n' +
      '╚██████╗   ██║   ██████╔╝███████╗██║  ██║███████║╚██████╗██║  ██║██║ ╚████║\n' +
      ' ╚═════╝   ╚═╝   ╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝╚═╝  ╚═══╝\n' +
      '\n' +
      ' Si tu lis ça, tu es des nôtres. 👾\n' +
      ' On recrute des talents en sécu — contact@rochercybersecurite.com\n' +
      ' Easter egg #2/6 découvert ✓\n',
    'color: #00e645; font-family: monospace; font-size: 11px;'
  );

bootstrapApplication(AppComponent, appConfig)
  .then(() => {
    if (isDevMode()) {
      import('axe-core').then(axe => {
        setTimeout(() => {
          axe.default.run(document, (err, results) => {
            if (err) return;
            if (results.violations.length) {
              console.group('[axe] Accessibility violations');
              results.violations.forEach(v => console.warn(v));
              console.groupEnd();
            }
          });
        }, 1000);
      });
    }
  })
  .catch(err => console.error(err));

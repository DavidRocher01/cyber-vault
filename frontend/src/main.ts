import { bootstrapApplication } from '@angular/platform-browser';
import { isDevMode } from '@angular/core';
import * as Sentry from '@sentry/angular';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';
import { environment } from './environments/environment';

if (!isDevMode()) {
  Sentry.init({
    dsn: 'https://6ef59d099fc59577740218c655c25005@o4511257225986048.ingest.de.sentry.io/4511257233653840',
    environment: 'production',
    release: environment.version,
    tracesSampleRate: 0.1,
    sendDefaultPii: false,
  });
}

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

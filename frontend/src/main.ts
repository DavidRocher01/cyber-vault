import { bootstrapApplication } from '@angular/platform-browser';
import { isDevMode } from '@angular/core';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';

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

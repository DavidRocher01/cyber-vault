import { ApplicationConfig, provideZoneChangeDetection, APP_INITIALIZER } from '@angular/core';
import { provideRouter, withInMemoryScrolling } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideHotToastConfig } from '@ngneat/hot-toast';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';

function initAOS(): () => Promise<void> {
  return () =>
    import('aos').then(({ default: AOS }) => {
      AOS.init({ duration: 400, easing: 'ease-out', once: true, mirror: false });
    });
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes, withInMemoryScrolling({ anchorScrolling: 'enabled', scrollPositionRestoration: 'enabled' })),
    provideAnimationsAsync(),
    provideHttpClient(withInterceptors([authInterceptor])),
    provideHotToastConfig({ position: 'bottom-center', duration: 3000 }),
    {
      provide: APP_INITIALIZER,
      useFactory: initAOS,
      multi: true,
    },
  ],
};

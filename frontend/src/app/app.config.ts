import {
  ApplicationConfig,
  provideZoneChangeDetection,
  APP_INITIALIZER,
  PLATFORM_ID,
} from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { provideRouter, withInMemoryScrolling } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withInterceptors, withFetch } from '@angular/common/http';
import { provideClientHydration } from '@angular/platform-browser';
import { provideHotToastConfig } from '@ngneat/hot-toast';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';

function initAOS(platformId: object): () => Promise<void> {
  return () => {
    if (!isPlatformBrowser(platformId)) return Promise.resolve();
    return import('aos').then(({ default: AOS }) => {
      AOS.init({ duration: 400, easing: 'ease-out', once: true, mirror: false });
    });
  };
}

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(
      routes,
      withInMemoryScrolling({ anchorScrolling: 'enabled', scrollPositionRestoration: 'enabled' })
    ),
    provideAnimationsAsync(),
    provideHttpClient(withInterceptors([authInterceptor]), withFetch()),
    provideClientHydration(),
    provideHotToastConfig({ position: 'bottom-center', duration: 3000 }),
    {
      provide: APP_INITIALIZER,
      useFactory: initAOS,
      deps: [PLATFORM_ID],
      multi: true,
    },
  ],
};

import { ApplicationConfig, ErrorHandler, provideZoneChangeDetection } from '@angular/core';
import { provideRouter, withInMemoryScrolling, TitleStrategy } from '@angular/router';
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import { provideHttpClient, withInterceptors, withFetch } from '@angular/common/http';
import { provideClientHydration } from '@angular/platform-browser';

import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth.interceptor';
import { ChunkReloadHandler } from './core/chunk-reload.handler';
import { SeoStrategy } from './core/seo.strategy';

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
    // Un onglet ouvert pendant un deploiement demande des morceaux que
    // `s3 sync --delete` a supprimes : la navigation echoue en silence et le
    // clic parait mort. Vu en production le 2026-08-07.
    { provide: ErrorHandler, useClass: ChunkReloadHandler },
    // Le titre venait deja de la route ; la description, elle, etait posee a la
    // main dans les composants — et manquait sur 9 des 23 pages du sitemap.
    { provide: TitleStrategy, useClass: SeoStrategy },
  ],
};

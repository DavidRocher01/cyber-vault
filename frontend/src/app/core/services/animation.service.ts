import { Injectable } from '@angular/core';
import { gsap } from 'gsap';

/**
 * AnimationService — centralises GSAP-based UI animations for Cyber-Vault.
 *
 * All methods accept a native HTMLElement and return the GSAP Tween so the
 * caller can chain or kill it if needed.
 */
@Injectable({ providedIn: 'root' })
export class AnimationService {
  /**
   * Smoothly reveals a password field / text element.
   * Fades in from transparent while sliding down a few pixels.
   */
  revealPassword(element: HTMLElement): gsap.core.Tween {
    return gsap.fromTo(
      element,
      { opacity: 0, y: -6, filter: 'blur(4px)' },
      {
        opacity: 1,
        y: 0,
        filter: 'blur(0px)',
        duration: 0.35,
        ease: 'power2.out',
      }
    );
  }

  /**
   * Smoothly hides a password field / text element.
   */
  hidePassword(element: HTMLElement): gsap.core.Tween {
    return gsap.to(element, {
      opacity: 0,
      y: -6,
      filter: 'blur(4px)',
      duration: 0.25,
      ease: 'power2.in',
    });
  }

  /**
   * Entrance animation for vault entry cards.
   * Fades in from below — complement AOS for imperatively added cards.
   */
  fadeInCard(element: HTMLElement): gsap.core.Tween {
    return gsap.fromTo(
      element,
      { opacity: 0, y: 20, scale: 0.97 },
      {
        opacity: 1,
        y: 0,
        scale: 1,
        duration: 0.4,
        ease: 'power3.out',
      }
    );
  }

  /**
   * Shake animation used to signal a validation error on a form or element.
   */
  shakeError(element: HTMLElement): gsap.core.Tween {
    return gsap.to(element, {
      keyframes: [
        { x: -8, duration: 0.07 },
        { x: 8, duration: 0.07 },
        { x: -6, duration: 0.07 },
        { x: 6, duration: 0.07 },
        { x: -4, duration: 0.07 },
        { x: 0, duration: 0.07 },
      ],
      ease: 'none',
    });
  }
}

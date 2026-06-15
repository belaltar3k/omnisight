import { Component, computed, inject, OnDestroy, OnInit, Output, EventEmitter, signal } from '@angular/core';
import { Router } from '@angular/router';
import { CookieService } from 'ngx-cookie-service';
import { ButtonComponent } from '@common/components/button/button.component';
import { InputComponent } from '@common/components/input/input';
import { AuthService } from '@core/services';

@Component({
  selector: 'app-header',
  standalone: true,
  imports: [ButtonComponent, InputComponent],
  templateUrl: './header.component.html',
})
export class HeaderComponent implements OnInit, OnDestroy {
  @Output() toggleSidebar = new EventEmitter<void>();

  readonly reducedMotion = signal(false);
  private motionQuery: MediaQueryList | undefined;
  private motionListener: ((e: MediaQueryListEvent) => void) | undefined;

  private readonly cookieService = inject(CookieService);
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  ngOnInit(): void {
    this.motionQuery = globalThis.matchMedia('(prefers-reduced-motion: reduce)');
    this.reducedMotion.set(this.motionQuery.matches);
    this.motionListener = (e) => this.reducedMotion.set(e.matches);
    this.motionQuery.addEventListener('change', this.motionListener);
  }

  ngOnDestroy(): void {
    if (this.motionQuery && this.motionListener) {
      this.motionQuery.removeEventListener('change', this.motionListener);
    }
  }

  readonly currentUserName = computed(() => {
    const token = this.cookieService.get('accessToken');
    if (!token) return 'User';
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return (payload.fullName as string) || (payload.email as string) || 'User';
    } catch {
      return 'User';
    }
  });

  logout(): void {
    const refreshToken = this.cookieService.get('refreshToken');
    const complete = () => {
      this.cookieService.delete('accessToken', '/');
      this.cookieService.delete('refreshToken', '/');
      this.router.navigate(['/login']);
    };

    if (refreshToken) {
      this.authService.logout({ refreshToken }).subscribe({ next: complete, error: complete });
    } else {
      complete();
    }
  }
}

import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { CookieService } from 'ngx-cookie-service';
import { AnchorComponent } from '@common/components/anchor/anchor.component';
import { ButtonComponent } from '@common/components/button/button.component';
import { InputComponent } from '@common/components/input/input';
import { AuthService } from '@core/services';
import { ILoginRequest, ILoginResponse } from '@shared/interfaces/auth';
import { BtnStylesEnum } from '@shared/enums';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [AnchorComponent, ButtonComponent, InputComponent, ReactiveFormsModule],
  templateUrl: './login.component.html',
})
export class LoginComponent {
  private readonly authService = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);
  private readonly cookieService = inject(CookieService);

  protected readonly isLoading = signal(false);
  protected readonly BtnStylesEnum = BtnStylesEnum;

  protected readonly loginForm = this.fb.nonNullable.group({
    email: ['', [Validators.required, Validators.email]],
    password: ['', [Validators.required]],
  });

  onLogin(): void {
    if (this.loginForm.invalid) {
      this.loginForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    const credentials: ILoginRequest = this.loginForm.getRawValue();

    this.authService.login(credentials).subscribe({
      next: (response: ILoginResponse) => {
        this.cookieService.set('accessToken', response.accessToken, { path: '/' });
        this.cookieService.set('refreshToken', response.refreshToken, { path: '/' });
        this.isLoading.set(false);
        void this.router.navigate(['/dashboard']);
      },
      error: () => {
        this.isLoading.set(false);
      },
    });
  }
}

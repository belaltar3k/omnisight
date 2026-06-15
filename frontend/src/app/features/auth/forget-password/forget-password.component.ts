import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { AnchorComponent } from '@common/components/anchor/anchor.component';
import { InputComponent } from '@common/components/input/input';
import { ButtonComponent } from '@common/components/button/button.component';
import { AuthService } from '@core/services';
import { BtnStylesEnum } from '@shared/enums';

@Component({
  selector: 'app-forget-password',
  imports: [ReactiveFormsModule, AnchorComponent, InputComponent, ButtonComponent],
  templateUrl: './forget-password.component.html',
})
export class ForgetPasswordComponent {
  private readonly fb = inject(FormBuilder);
  private readonly authService = inject(AuthService);

  protected readonly isLoading = signal(false);
  protected readonly isSubmitted = signal(false);
  protected readonly BtnStylesEnum = BtnStylesEnum;

  protected readonly forgotPasswordForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
  });

  submit(): void {
    if (this.forgotPasswordForm.invalid) {
      this.forgotPasswordForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    const { email } = this.forgotPasswordForm.getRawValue();

    this.authService.forgotPassword({ email: email! }).subscribe({
      next: () => {
        this.isLoading.set(false);
        this.isSubmitted.set(true);
      },
      error: () => {
        this.isLoading.set(false);
      },
    });
  }
}

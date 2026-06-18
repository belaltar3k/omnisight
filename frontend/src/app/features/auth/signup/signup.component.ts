import { Component, inject, signal } from "@angular/core";
import {
  AbstractControl,
  FormBuilder,
  ReactiveFormsModule,
  ValidationErrors,
  Validators,
} from "@angular/forms";
import { Router } from "@angular/router";
import { AnchorComponent } from "@common/components/anchor/anchor.component";
import { ButtonComponent } from "@common/components/button/button.component";
import { InputComponent } from "@common/components/input/input";
import { AuthService } from "@core/services";
import {BtnStylesEnum, UserRole} from "@shared/enums";
import { IRegisterResponse } from "@shared/interfaces/auth";

@Component({
  selector: "app-signup",
  imports: [ReactiveFormsModule, AnchorComponent, InputComponent, ButtonComponent],
  templateUrl: "./signup.component.html",
})
export class SignupComponent {
  private readonly authService = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly router = inject(Router);

  protected readonly isLoading = signal(false);

  protected readonly signupForm = this.fb.nonNullable.group(
    {
      fullName: ["", [Validators.required]],
      email: ["", [Validators.required, Validators.email]],
      password: ["", [Validators.required, Validators.minLength(8)]],
      confirmPassword: ["", [Validators.required]],
    },
    {
      validators: this.passwordsMatchValidator,
    },
  );

  signup(): void {
    if (this.signupForm.invalid) {
      this.signupForm.markAllAsTouched();
      return;
    }

    this.isLoading.set(true);
    const { confirmPassword, ...formValue } = this.signupForm.getRawValue();

    this.authService
      .register({
        ...formValue,
        role: UserRole.Viewer,
      })
      .subscribe({
        next: (response: IRegisterResponse) => {
          console.log("Signup successful:", response);
          this.isLoading.set(false);
          void this.router.navigate(["/login"]);
        },
        error: (error: Error) => {
          console.error("Signup failed:", error);
          this.isLoading.set(false);
        },
      });
  }

  private passwordsMatchValidator(
    control: AbstractControl,
  ): ValidationErrors | null {
    const password = control.get("password")?.value;
    const confirmPassword = control.get("confirmPassword")?.value;

    return password && confirmPassword && password !== confirmPassword
      ? { passwordMismatch: true }
      : null;
  }

  protected readonly BtnStylesEnum = BtnStylesEnum;
}
import { Component, effect, inject, signal } from '@angular/core';
import { AbstractControl, FormBuilder, FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { ModalService } from '@core/services/modal.service';
import { BtnStylesEnum } from '@shared/enums';
import { ButtonComponent } from '@common/components/button/button.component';
import { InputComponent } from '@common/components/input/input';

@Component({
  selector: 'app-modal',
  standalone: true,
  imports: [ReactiveFormsModule, ButtonComponent, InputComponent],
  templateUrl: './modal.component.html',
})
export class ModalComponent {
  private readonly modalService = inject(ModalService);
  private readonly fb = inject(FormBuilder);

  protected readonly config = this.modalService.config;
  protected readonly isOpen = this.modalService.isOpen;
  protected readonly isSubmitting = signal(false);
  protected readonly form = signal(this.fb.group({}));
  protected readonly BtnStylesEnum = BtnStylesEnum;

  constructor() {
    effect(
      () => {
        const config = this.config();
        if (!config) return;
        const controls: Record<string, AbstractControl> = {};
        for (const field of config.fields) {
          controls[field.key] = new FormControl(
            '',
            field.required ? Validators.required : [],
          );
        }
        this.form.set(this.fb.group(controls));
      },
      { allowSignalWrites: true },
    );
  }

  protected submit(): void {
    if (this.form().invalid || this.isSubmitting()) return;
    const config = this.config();
    if (!config) return;

    this.isSubmitting.set(true);
    config.onSubmit(this.form().value).subscribe({
      next: () => {
        this.isSubmitting.set(false);
        config.onSuccess?.();
        this.modalService.close();
      },
      error: () => {
        this.isSubmitting.set(false);
      },
    });
  }

  protected close(): void {
    this.modalService.close();
  }
}

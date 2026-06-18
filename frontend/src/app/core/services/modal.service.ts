import { Injectable, computed, signal } from '@angular/core';
import { IModalConfig } from '@shared/interfaces/modal';

@Injectable({ providedIn: 'root' })
export class ModalService {
  private readonly _config = signal<IModalConfig | null>(null);

  readonly config = this._config.asReadonly();
  readonly isOpen = computed(() => this._config() !== null);

  open(config: IModalConfig): void {
    this._config.set(config);
  }

  close(): void {
    this._config.set(null);
  }
}

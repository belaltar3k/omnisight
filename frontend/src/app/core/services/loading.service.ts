import { Injectable, signal, computed } from "@angular/core";

@Injectable({ providedIn: "root" })
export class LoadingService {
  private readonly activeRequests = signal(0);
  readonly isLoading = computed(() => this.activeRequests() > 0);

  start() {
    this.activeRequests.update((n) => n + 1);
  }
  stop() {
    this.activeRequests.update((n) => Math.max(0, n - 1));
  }
}

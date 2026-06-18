import { computed, inject, Injectable, signal } from '@angular/core';
import { CookieService } from 'ngx-cookie-service';
import { UserRole } from '@shared/enums';

@Injectable({ providedIn: 'root' })
export class PermissionsService {
  private readonly cookieService = inject(CookieService);

  private readonly role = signal<UserRole | null>(this.readRoleFromToken());

  readonly isAdmin = computed(() => this.role() === UserRole.Admin);
  readonly isSupervisor = computed(() => this.role() === UserRole.Supervisor);
  readonly isSecurityGuard = computed(() => this.role() === UserRole.SecurityGuard);

  readonly canManageUsers = computed(() => this.isAdmin());
  readonly canManageEdgeNodes = computed(() => this.isAdmin());
  readonly canDeleteCamera = computed(() => this.isAdmin());
  readonly canDeleteZone = computed(() => this.isAdmin());
  readonly canDeleteIncident = computed(() => this.isAdmin());

  readonly canCreateCamera = computed(() => this.isAdmin() || this.isSupervisor());
  readonly canEditCamera = computed(() => this.isAdmin() || this.isSupervisor());
  readonly canCreateZone = computed(() => this.isAdmin() || this.isSupervisor());
  readonly canEditZone = computed(() => this.isAdmin() || this.isSupervisor());
  readonly canManageZoneAssignments = computed(() => this.isAdmin() || this.isSupervisor());
  readonly canAcknowledgeIncident = computed(() => this.isAdmin() || this.isSupervisor());
  readonly canResolveIncident = computed(() => this.isAdmin() || this.isSupervisor());
  readonly canEscalateIncident = computed(() => this.isAdmin() || this.isSupervisor());

  readonly canViewEdgeNodes = computed(() => this.isAdmin() || this.isSupervisor());
  readonly canViewAnalytics = computed(() => this.isAdmin() || this.isSupervisor());

  refreshFromToken(): void {
    this.role.set(this.readRoleFromToken());
  }

  private readRoleFromToken(): UserRole | null {
    const token = this.cookieService.get('accessToken');
    if (!token) return null;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return (payload.role as UserRole) ?? null;
    } catch {
      return null;
    }
  }
}

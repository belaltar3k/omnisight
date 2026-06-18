import { AsyncPipe, DatePipe } from "@angular/common";
import { Component, inject } from "@angular/core";
import { ButtonComponent } from "@common/components/button/button.component";
import { AlertService } from "@core/services";
import { BtnStylesEnum, Priority } from "@shared/enums";
import { IAlert } from "@shared/interfaces/alert";
import { ToastrService } from "ngx-toastr";
import { Router } from "@angular/router";

@Component({
  selector: "app-alert-list",
  standalone: true,
  templateUrl: "./alert-list.component.html",
  imports: [AsyncPipe, DatePipe, ButtonComponent],
})
export class AlertListComponent {
  private readonly alertService = inject(AlertService);
  private readonly toastr = inject(ToastrService);
  private readonly router = inject(Router);

  alerts$ = this.alertService.getAlerts();

  priorityClass(priority: Priority): string {
    const map: Record<Priority, string> = {
      [Priority.Critical]: "bg-red-500/20 text-red-400",
      [Priority.High]: "bg-orange-500/20 text-orange-400",
      [Priority.Medium]: "bg-yellow-500/20 text-yellow-400",
      [Priority.Low]: "bg-slate-500/20 text-slate-400",
    };
    return map[priority] ?? "bg-yellow-500/20 text-yellow-400";
  }

  acknowledge(alert: IAlert): void {
    this.alertService.acknowledgeAlert(alert.alertId).subscribe({
      next: () => {
        this.toastr.success("Alert acknowledged");
        this.alerts$ = this.alertService.getAlerts();
      },
    });
  }

  openPreferences(): void {
    this.router.navigate(["/alerts/preferences"]);
  }

  protected readonly BtnStylesEnum = BtnStylesEnum;
}

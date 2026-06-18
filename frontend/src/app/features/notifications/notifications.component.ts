import { AsyncPipe } from "@angular/common";
import { Component, inject } from "@angular/core";
import { ButtonComponent } from "@common/components/button/button.component";
import { NotificationService } from "@core/services";
import {BtnStylesEnum} from "@shared/enums";

@Component({
  selector: "app-notifications",
  standalone: true,
  templateUrl: "./notifications.component.html",
  imports: [AsyncPipe, ButtonComponent],
})
export class NotificationsComponent {
  private readonly notificationService = inject(NotificationService);

  notifications$ = this.notificationService.getNotifications();
  protected readonly BtnStylesEnum = BtnStylesEnum;
}
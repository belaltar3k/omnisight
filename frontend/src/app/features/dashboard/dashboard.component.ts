import { Component, inject } from "@angular/core";
import { AsyncPipe } from "@angular/common";
import { DeviceListComponent } from "./components/device-list/device-list.component";
import { EventDetailsComponent } from "./components/event-details/event-details.component";
import { CameraFeedComponent } from "./components/camera-feed/camera-feed.component";
import { EventsListComponent } from "./components/events-list/events-list.component";
import { AnalyticsService, CameraService } from "@core/services";

@Component({
  selector: "app-dashboard",
  standalone: true,
  imports: [
    DeviceListComponent,
    EventDetailsComponent,
    CameraFeedComponent,
    EventsListComponent,
    AsyncPipe,
  ],
  templateUrl: "./dashboard.component.html",
})
export class DashboardComponent {
  private readonly analyticsService = inject(AnalyticsService);
  private readonly cameraService = inject(CameraService);

  cameras$ = this.cameraService.getCameras();

}

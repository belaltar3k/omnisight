import { Component, inject } from "@angular/core";
import { DeviceListComponent } from "./components/device-list/device-list.component";
import { EventDetailsComponent } from "./components/event-details/event-details.component";
import { CameraFeedComponent } from "./components/camera-feed/camera-feed.component";
import { EventsListComponent } from "./components/events-list/events-list.component";
import {
  CameraService,
  ZoneService,
  IncidentService,
  AlertService,
} from "@core/services";
import { combineLatest, map } from "rxjs";

@Component({
  selector: "app-dashboard",
  standalone: true,
  imports: [
    DeviceListComponent,
    EventDetailsComponent,
    CameraFeedComponent,
    EventsListComponent,
  ],
  templateUrl: "./dashboard.component.html",
})
export class DashboardComponent {
  private readonly cameraService = inject(CameraService);
  private readonly zoneService = inject(ZoneService);
  private readonly incidentService = inject(IncidentService);
  private readonly alertService = inject(AlertService);

  // Load camera and zone data
  cameras$ = this.cameraService.getCameras();
  zones$ = this.zoneService.getZones();
  incidents$ = this.incidentService.getIncidents();
  alerts$ = this.alertService.getAlerts();

  // Aggregate dashboard metrics
  dashboardData$ = combineLatest([
    this.cameras$,
    this.zones$,
    this.incidents$,
    this.alerts$,
  ]).pipe(
    map(([cameras, zones, incidents, alerts]) => ({
      totalCameras: cameras?.length || 0,
      onlineCameras: cameras?.filter((c) => c.status === "online").length || 0,
      totalZones: zones?.length || 0,
      recentIncidents: incidents?.slice(0, 5) || [],
      criticalAlerts:
        alerts?.filter((a) => a.priority === "critical").length || 0,
      highAlerts: alerts?.filter((a) => a.priority === "high").length || 0,
    })),
  );
}

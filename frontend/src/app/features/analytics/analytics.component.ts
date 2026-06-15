import { Component, signal, inject } from "@angular/core";
import { ButtonComponent } from "@common/components/button/button.component";
import {
  CameraService,
  ZoneService,
  IncidentService,
  AlertService,
} from "@core/services";

type AnalyticsTab =
  | "motion-chaos"
  | "audio-triggers"
  | "vlm-performance"
  | "incidents"
  | "heatmap"
  | "response-times";

@Component({
  selector: "app-analytics",
  standalone: true,
  imports: [ButtonComponent],
  templateUrl: "./analytics.component.html",
})
export class AnalyticsComponent {
  private readonly cameraService = inject(CameraService);
  private readonly zoneService = inject(ZoneService);
  private readonly incidentService = inject(IncidentService);
  private readonly alertService = inject(AlertService);

  activeTab = signal<AnalyticsTab>("motion-chaos");

  tabs: { id: AnalyticsTab; label: string }[] = [
    { id: "motion-chaos", label: "Motion Chaos" },
    { id: "audio-triggers", label: "Audio Triggers" },
    { id: "vlm-performance", label: "VLM Performance" },
    { id: "incidents", label: "Incidents" },
    { id: "heatmap", label: "Crime Heatmap" },
    { id: "response-times", label: "Response Times" },
  ];

  cameras$ = this.cameraService.getCameras();
  zones$ = this.zoneService.getZones();
  incidents$ = this.incidentService.getIncidents();
  alerts$ = this.alertService.getAlerts();

  get currentTab() {
    return this.tabs.find((t) => t.id === this.activeTab());
  }
}

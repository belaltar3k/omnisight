import { Component, inject } from "@angular/core";
import { RouterLink } from "@angular/router";
import { AsyncPipe, DatePipe } from "@angular/common";
import { ButtonComponent } from "@common/components/button/button.component";
import { StatusBadgeComponent } from "@common/components/status-badge/status-badge.component";
import { PriorityBadgeComponent } from "@common/components/priority-badge/priority-badge.component";
import { IncidentService } from "@core/services";
import {BtnStylesEnum} from "@shared/enums";

interface Incident {
  id: string;
  crimeType: string;
  confidence: number;
  status:
    | "new"
    | "acknowledged"
    | "investigating"
    | "escalated"
    | "resolved"
    | "false_positive"
    | "vlm_verifying"
    | "dispatched"
    | "on_scene";
  priority: "critical" | "high" | "medium" | "low";
  camera: string;
  time: string;
}

@Component({
  selector: "app-incident-list",
  standalone: true,
  imports: [
    RouterLink,
    ButtonComponent,
    StatusBadgeComponent,
    PriorityBadgeComponent,
    AsyncPipe,
    DatePipe
  ],
  templateUrl: "./incident-list.component.html",
})
export class IncidentListComponent {
  private readonly incidentService = inject(IncidentService);

  incidents$ = this.incidentService.getIncidents();
    protected readonly BtnStylesEnum = BtnStylesEnum;
}
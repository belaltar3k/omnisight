import { Component, inject } from "@angular/core";
import { RouterLink } from "@angular/router";
import { AsyncPipe, DatePipe } from "@angular/common";
import { ButtonComponent } from "@common/components/button/button.component";
import { StatusBadgeComponent } from "@common/components/status-badge/status-badge.component";
import { PriorityBadgeComponent } from "@common/components/priority-badge/priority-badge.component";
import { IncidentService } from "@core/services";
import {BtnStylesEnum} from "@shared/enums";


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
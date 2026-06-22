import { Component, inject } from '@angular/core';
import { AsyncPipe, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { IncidentService } from '@core/services';

@Component({
  selector: 'app-events-list',
  standalone: true,
  imports: [AsyncPipe, DatePipe, RouterLink],
  templateUrl: './events-list.component.html',
  styles: [`:host { display: contents; }`],
})
export class EventsListComponent {
  private readonly incidentService = inject(IncidentService);
  incidents$ = this.incidentService.getIncidents({ limit: 10 });
}

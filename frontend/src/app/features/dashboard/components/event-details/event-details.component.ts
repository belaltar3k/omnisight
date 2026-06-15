import { Component } from '@angular/core';
import { ButtonComponent } from "@common/components/button/button.component";

@Component({
  selector: 'app-event-details',
  standalone: true,
  imports: [ButtonComponent],
  templateUrl: './event-details.component.html',
})
export class EventDetailsComponent {}

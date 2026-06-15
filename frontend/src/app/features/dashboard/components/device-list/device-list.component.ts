import { Component } from '@angular/core';
import { ButtonComponent } from "@common/components/button/button.component";

@Component({
  selector: 'app-device-list',
  standalone: true,
  imports: [ButtonComponent],
  templateUrl: './device-list.component.html',
})
export class DeviceListComponent {
  devices = [
    { name: 'Ware House Cam 1', location: 'Building A' },
    { name: 'Terminal C',        location: 'Hanger A'   },
    { name: 'Server Room A2',    location: 'Building A' },
    { name: 'Ware House Cam 3',  location: 'Building A' },
    { name: 'Ware House Cam 4',  location: 'Building A' },
    { name: 'Admin Room Cam',    location: 'Building D' },
    { name: 'Parking Garage 1',  location: 'Building C' },
    { name: 'Office Space 201',  location: 'Building A' },
  ];
}

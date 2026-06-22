import { Component, inject } from '@angular/core';
import { AsyncPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { CameraService } from '@core/services';

@Component({
  selector: 'app-device-list',
  standalone: true,
  imports: [AsyncPipe, RouterLink],
  templateUrl: './device-list.component.html',
})
export class DeviceListComponent {
  private readonly cameraService = inject(CameraService);
  cameras$ = this.cameraService.getCameras();
}

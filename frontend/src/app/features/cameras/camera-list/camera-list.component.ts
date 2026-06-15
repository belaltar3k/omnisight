import { Component, inject } from "@angular/core";
import { AsyncPipe, TitleCasePipe } from "@angular/common";
import { ButtonComponent } from "@common/components/button/button.component";
import { CameraService } from "@core/services";
import { ModalService } from "@core/services/modal.service";
import { BtnStylesEnum } from "@shared/enums";
import { ICamera } from "@shared/interfaces/camera";
import { ToastrService } from "ngx-toastr";

@Component({
  selector: "app-camera-list",
  standalone: true,
  imports: [TitleCasePipe, AsyncPipe, ButtonComponent],
  templateUrl: "./camera-list.component.html",
})
export class CameraListComponent {
  private readonly cameraService = inject(CameraService);
  private readonly modalService = inject(ModalService);
  private readonly toastr = inject(ToastrService);

  cameras$ = this.cameraService.getCameras();
  protected readonly BtnStylesEnum = BtnStylesEnum;

  openAddCameraModal(): void {
    this.modalService.open({
      title: 'Add Camera',
      submitLabel: 'Add Camera',
      fields: [
        { key: 'name', label: 'Camera Name', type: 'text', placeholder: 'Enter camera name', required: true },
        { key: 'code', label: 'Code', type: 'text', placeholder: 'e.g. CAM-ENT-001', required: true },
        { key: 'rtspUrl', label: 'RTSP URL', type: 'text', placeholder: 'rtsp://192.168.1.200:554/stream1', required: true },
        { key: 'zoneId', label: 'Zone ID', type: 'text', placeholder: 'Zone UUID', required: true },
        { key: 'edgeNodeId', label: 'Edge Node ID', type: 'text', placeholder: 'Edge Node UUID', required: true },
        { key: 'targetFps', label: 'Target FPS', type: 'number', placeholder: '30' },
        { key: 'resolutionWidth', label: 'Resolution Width', type: 'number', placeholder: '1920' },
        { key: 'resolutionHeight', label: 'Resolution Height', type: 'number', placeholder: '1080' },
      ],
      onSubmit: (data) => this.cameraService.createCamera(data as never),
      onSuccess: () => { this.cameras$ = this.cameraService.getCameras(); },
    });
  }

  openEditCameraModal(camera: ICamera): void {
    this.modalService.open({
      title: 'Edit Camera',
      submitLabel: 'Save Changes',
      fields: [
        { key: 'name', label: 'Camera Name', type: 'text', placeholder: camera.name, required: true },
        { key: 'rtspUrl', label: 'RTSP URL', type: 'text', placeholder: camera.rtspUrl, required: true },
        { key: 'zoneId', label: 'Zone ID', type: 'text', placeholder: camera.zoneId, required: true },
        { key: 'edgeNodeId', label: 'Edge Node ID', type: 'text', placeholder: camera.edgeNodeId, required: true },
        { key: 'targetFps', label: 'Target FPS', type: 'number', placeholder: String(camera.targetFps ?? 30) },
      ],
      onSubmit: (data) => this.cameraService.updateCamera(camera.id, data as never),
      onSuccess: () => { this.cameras$ = this.cameraService.getCameras(); },
    });
  }

  deleteCamera(camera: ICamera): void {
    if (!confirm(`Delete camera "${camera.name}"? This cannot be undone.`)) return;
    this.cameraService.deleteCamera(camera.id).subscribe({
      next: () => {
        this.toastr.success('Camera deleted');
        this.cameras$ = this.cameraService.getCameras();
      },
    });
  }
}
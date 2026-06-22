import { Component, input } from "@angular/core";

@Component({
  selector: "app-camera-feed",
  standalone: true,
  imports: [],
  templateUrl: "./camera-feed.component.html",
  styles: [`:host { display: contents; }`],
})
export class CameraFeedComponent {
  label = input("");
  cameraCode = input<string | null>(null);
  showControls = input(false);
  showClose = input(false);

  get streamUrl(): string | null {
    const code = this.cameraCode();
    return code ? `/stream/${code}` : null;
  }

  onStreamError(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }
}

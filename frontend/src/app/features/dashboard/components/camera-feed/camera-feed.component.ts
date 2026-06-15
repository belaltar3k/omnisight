import { Component, InputSignal, inject, input } from "@angular/core";
import { ButtonComponent } from "@common/components/button/button.component";
import { DomSanitizer, SafeHtml } from "@angular/platform-browser";

export type ImageType =
  | "parking"
  | "checkin"
  | "server"
  | "office"
  | "terminal";

@Component({
  selector: "app-camera-feed",
  standalone: true,
  imports: [ButtonComponent],
  templateUrl: "./camera-feed.component.html",
  styles: [
    `
      :host {
        display: contents;
      }
    `,
  ],
})
export class CameraFeedComponent {
  private readonly sanitizer = inject(DomSanitizer);

  label: InputSignal<string> = input("");
  live: InputSignal<boolean> = input(true);
  showControls: InputSignal<boolean> = input(false);
  showClose: InputSignal<boolean> = input(false);
  showLivePercent: InputSignal<boolean> = input(false);
  imageType: InputSignal<ImageType> = input<ImageType>("parking");

  timelineBars = new Array(24).fill(0);
  timeLabels = [
    "19:35",
    "19:38",
    "19:41",
    "19:44",
    "19:47",
    "19:50",
    "19:53",
    "19:56",
    "19:59",
    "20:03",
    "20:06",
    "20:09",
    "20:13",
    "20:16",
  ];

  get sceneSvg(): SafeHtml {
    return this.sanitizer.bypassSecurityTrustHtml(this.getRawSvg());
  }

  getRawSvg(): string {
    const scenes: Record<ImageType, string> = {
      parking: `<svg viewBox="0 0 400 220" class="w-full h-full opacity-60" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="pg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1e293b"/><stop offset="100%" stop-color="#0f172a"/></linearGradient></defs><rect width="400" height="220" fill="url(#pg)"/><line x1="0" y1="60" x2="400" y2="60" stroke="#334155" stroke-width="1"/><rect x="40" y="40" width="12" height="180" fill="#1e293b"/><rect x="140" y="40" width="12" height="180" fill="#1e293b"/><rect x="240" y="40" width="12" height="180" fill="#1e293b"/><rect x="340" y="40" width="12" height="180" fill="#1e293b"/><line x1="0" y1="120" x2="400" y2="120" stroke="#334155" stroke-width="0.5" stroke-dasharray="20,10"/><line x1="0" y1="160" x2="400" y2="160" stroke="#334155" stroke-width="0.5" stroke-dasharray="20,10"/><ellipse cx="300" cy="170" rx="60" ry="20" fill="#ef4444" opacity="0.7"/><rect x="255" y="150" width="90" height="22" rx="6" fill="#dc2626" opacity="0.8"/><rect x="265" y="140" width="70" height="14" rx="4" fill="#b91c1c" opacity="0.8"/><circle cx="80" cy="50" r="6" fill="#fef08a" opacity="0.4"/><circle cx="200" cy="50" r="6" fill="#fef08a" opacity="0.4"/><circle cx="320" cy="50" r="6" fill="#fef08a" opacity="0.4"/></svg>`,
      checkin: `<svg viewBox="0 0 400 220" class="w-full h-full opacity-60" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="cg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1e3a5f"/><stop offset="100%" stop-color="#0d1f3c"/></linearGradient></defs><rect width="400" height="220" fill="url(#cg)"/><rect x="0" y="0" width="400" height="40" fill="#0f2a4a"/><rect x="20" y="130" width="50" height="50" rx="2" fill="#1e3a5f"/><rect x="80" y="130" width="50" height="50" rx="2" fill="#1e3a5f"/><rect x="140" y="130" width="50" height="50" rx="2" fill="#1e3a5f"/><rect x="200" y="130" width="50" height="50" rx="2" fill="#1e3a5f"/><rect x="260" y="130" width="50" height="50" rx="2" fill="#1e3a5f"/><rect x="320" y="130" width="60" height="50" rx="2" fill="#1e3a5f"/><circle cx="55" cy="100" r="7" fill="#94a3b8" opacity="0.6"/><circle cx="115" cy="98" r="7" fill="#94a3b8" opacity="0.6"/><circle cx="175" cy="102" r="7" fill="#94a3b8" opacity="0.6"/><circle cx="235" cy="99" r="7" fill="#94a3b8" opacity="0.6"/><circle cx="295" cy="101" r="7" fill="#94a3b8" opacity="0.6"/></svg>`,
      server: `<svg viewBox="0 0 400 220" class="w-full h-full opacity-60" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="sg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#0f1a2e"/><stop offset="100%" stop-color="#060d1a"/></linearGradient></defs><rect width="400" height="220" fill="url(#sg)"/><rect x="20" y="20" width="55" height="190" rx="2" fill="#0d2040"/><rect x="90" y="20" width="55" height="190" rx="2" fill="#0d2040"/><rect x="160" y="20" width="55" height="190" rx="2" fill="#0d2040"/><rect x="230" y="20" width="55" height="190" rx="2" fill="#0d2040"/><rect x="300" y="20" width="55" height="190" rx="2" fill="#0d2040"/><circle cx="68" cy="37" r="2" fill="#22c55e" opacity="0.8"/><circle cx="138" cy="37" r="2" fill="#3b82f6" opacity="0.8"/><circle cx="68" cy="57" r="2" fill="#3b82f6" opacity="0.8"/><circle cx="138" cy="57" r="2" fill="#22c55e" opacity="0.8"/><circle cx="208" cy="37" r="2" fill="#22c55e" opacity="0.8"/><circle cx="278" cy="37" r="2" fill="#3b82f6" opacity="0.8"/></svg>`,
      office: `<svg viewBox="0 0 400 220" class="w-full h-full opacity-60" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="og" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1a3320"/><stop offset="100%" stop-color="#0d1f14"/></linearGradient></defs><rect width="400" height="220" fill="url(#og)"/><rect x="0" y="0" width="400" height="50" fill="#0f2518"/><ellipse cx="60" cy="150" rx="25" ry="40" fill="#166534" opacity="0.8"/><ellipse cx="55" cy="140" rx="15" ry="30" fill="#15803d" opacity="0.9"/><rect x="55" y="185" width="10" height="25" fill="#713f12"/><ellipse cx="350" cy="145" rx="30" ry="45" fill="#166534" opacity="0.7"/><rect x="120" y="150" width="80" height="35" rx="5" fill="#065f46" opacity="0.8"/><rect x="210" y="150" width="80" height="35" rx="5" fill="#065f46" opacity="0.8"/></svg>`,
      terminal: `<svg viewBox="0 0 400 220" class="w-full h-full opacity-60" xmlns="http://www.w3.org/2000/svg"><defs><linearGradient id="tg" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1a2a4a"/><stop offset="100%" stop-color="#0a1528"/></linearGradient></defs><rect width="400" height="220" fill="url(#tg)"/><rect x="0" y="0" width="400" height="30" fill="#0f1e38"/><rect x="20" y="30" width="80" height="100" rx="2" fill="#1e3a5f" opacity="0.5"/><rect x="110" y="30" width="80" height="100" rx="2" fill="#1e3a5f" opacity="0.5"/><rect x="200" y="30" width="80" height="100" rx="2" fill="#1e3a5f" opacity="0.5"/><rect x="290" y="30" width="90" height="100" rx="2" fill="#1e3a5f" opacity="0.5"/><circle cx="30" cy="145" r="5" fill="#64748b" opacity="0.5"/><circle cx="80" cy="143" r="5" fill="#64748b" opacity="0.5"/><circle cx="130" cy="145" r="5" fill="#64748b" opacity="0.5"/><circle cx="180" cy="143" r="5" fill="#64748b" opacity="0.5"/><circle cx="230" cy="145" r="5" fill="#64748b" opacity="0.5"/><circle cx="280" cy="143" r="5" fill="#64748b" opacity="0.5"/><circle cx="330" cy="145" r="5" fill="#64748b" opacity="0.5"/><circle cx="380" cy="143" r="5" fill="#64748b" opacity="0.5"/></svg>`,
    };
    return scenes[this.imageType()] ?? "";
  }
}

import { Component, signal, inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { ButtonComponent } from "@common/components/button/button.component";
import { InputComponent } from "@common/components/input/input";
import { SettingsService } from "@core/services";

type SettingsTab = "general" | "security" | "api-keys" | "audit-logs";
type SettingsItem =
  | {
      label: string;
      description: string;
      type: "input";
      value: string;
    }
  | {
      label: string;
      description: string;
      type: "toggle";
      value: boolean;
    };

@Component({
  selector: "app-settings",
  standalone: true,
  imports: [FormsModule, ButtonComponent, InputComponent],
  templateUrl: "./settings.component.html",
})
export class SettingsComponent {
  private readonly settingsService = inject(SettingsService);

  activeTab = signal<SettingsTab>("general");
  settings$ = this.settingsService.getSettings();

  tabs: { id: SettingsTab; label: string }[] = [
    { id: "general", label: "General" },
    { id: "security", label: "Security" },
    { id: "api-keys", label: "API Keys" },
    { id: "audit-logs", label: "Audit Logs" },
  ];

  get currentSettings(): SettingsItem[] {
    return [
      {
        label: "System Name",
        description: "Display name for this OmniSight installation",
        type: "input",
        value: "OmniSight Production",
      },
      {
        label: "VLM Confidence Threshold",
        description: "Minimum confidence to trigger VLM verification",
        type: "input",
        value: "0.75",
      },
      {
        label: "MFA Required",
        description: "Enforce MFA for all user accounts",
        type: "toggle",
        value: true,
      },
      {
        label: "Real-time Alerts",
        description: "Enable WebSocket push notifications",
        type: "toggle",
        value: true,
      },
      {
        label: "Data Retention (days)",
        description: "How long to keep incident data",
        type: "input",
        value: "90",
      },
      {
        label: "Maintenance Mode",
        description: "Take system offline for maintenance",
        type: "toggle",
        value: false,
      },
    ];
  }

  settingId(label: string): string {
    return label.toLowerCase().replaceAll(" ", "-");
  }
}

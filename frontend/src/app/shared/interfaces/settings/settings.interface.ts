export interface ISettings {
  id?: string;
  systemName: string;
  maxCameras: number;
  maxZones: number;
  retentionDays: number;
  alertNotificationsEnabled: boolean;
  emailNotificationsEnabled: boolean;
  updatedAt?: string;
}

export interface IUpdateSettingsRequest {
  systemName?: string;
  maxCameras?: number;
  maxZones?: number;
  retentionDays?: number;
  alertNotificationsEnabled?: boolean;
  emailNotificationsEnabled?: boolean;
}

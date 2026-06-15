import { AlertStatus, AlertType, Priority } from '@shared/enums';

export interface IAlert {
  alertId: string;
  incidentId: string;
  userId: string;
  alertType: AlertType;
  status: AlertStatus;
  priority: Priority;
  sentAt: string;
  acknowledgedAt?: string;
  deliveredAt?: string;
}

export interface IAlertPreferences {
  userId: string;
  preferences: {
    pushEnabled: boolean;
    smsEnabled: boolean;
    emailEnabled: boolean;
    quietHours?: {
      enabled: boolean;
      start: string;
      end: string;
      timezone: string;
      exceptions: string[];
    };
    alertFilters?: {
      crimeTypes?: string[];
      minConfidence?: number;
      zones?: string[];
    };
  };
}

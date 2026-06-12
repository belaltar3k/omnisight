import { Injectable, Logger, OnModuleInit } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { HttpService } from '@nestjs/axios';
import { JwtService } from '@nestjs/jwt';
import { firstValueFrom, timeout } from 'rxjs';
import * as admin from 'firebase-admin';
import { DeviceTokensService } from '../device-tokens/device-tokens.service';
import { DeviceToken } from '../device-tokens/entities/device-token.entity';

export interface IncidentNewEvent {
  incidentId: string;
  cameraCode: string;
  zoneId: string;
  crimeType: string;
  priority: string;
  confidence: number;
  detectedAt: string;
  edgeNodeCode: string;
}

export interface IncidentStatusChangedEvent {
  incidentId: string;
  cameraCode: string;
  zoneId: string;
  fromStatus: string;
  toStatus: string;
  assignedTo?: string;
  performedBy: string;
}

@Injectable()
export class AlertsService implements OnModuleInit {
  private readonly logger = new Logger(AlertsService.name);
  private readonly userServiceUrl: string;
  private readonly alertServiceToken: string;
  private firebaseEnabled = false;

  constructor(
    private readonly deviceTokensService: DeviceTokensService,
    private readonly httpService: HttpService,
    private readonly configService: ConfigService,
    private readonly jwtService: JwtService,
  ) {
    this.userServiceUrl = this.configService.get<string>('USER_SERVICE_URL') ?? 'http://localhost:3004';
    this.alertServiceToken = this.jwtService.sign(
      { sub: 'alert-service', email: 'alert-service@internal', role: 'alert_service' },
      { expiresIn: '10y' },
    );
  }

  onModuleInit() {
    const projectId   = this.configService.get<string>('FIREBASE_PROJECT_ID');
    const clientEmail = this.configService.get<string>('FIREBASE_CLIENT_EMAIL');
    const privateKey  = this.configService.get<string>('FIREBASE_PRIVATE_KEY');

    if (projectId && clientEmail && privateKey) {
      try {
        admin.initializeApp({
          credential: admin.credential.cert({
            projectId,
            clientEmail,
            privateKey: privateKey.replace(/\\n/g, '\n'),
          }),
        });
        this.firebaseEnabled = true;
        this.logger.log('Firebase Admin initialized — FCM push enabled');
      } catch (err: any) {
        this.logger.warn(`Firebase init failed (${err.message}) — running in LOG mode`);
      }
    } else {
      this.logger.warn('Firebase not configured — running in LOG mode (no real push sent)');
    }
  }

  async handleIncidentNew(event: IncidentNewEvent) {
    this.logger.log(`New incident event: ${JSON.stringify(event)}`);

    const tokens = await this.getZoneUserTokens(event.zoneId);

    if (tokens.length === 0) {
      this.logger.warn(`No device tokens for zone ${event.zoneId} — skipping push`);
      return;
    }

    await this.sendToTokens(
      tokens.map(t => t.fcmToken),
      {
        title: `🚨 New Incident Detected`,
        body: `${event.crimeType.toUpperCase()} — Camera ${event.cameraCode} | Priority: ${event.priority}`,
      },
      {
        incidentId: event.incidentId,
        type: 'incident.new',
        crimeType: event.crimeType,
        priority: event.priority,
        cameraCode: event.cameraCode,
        zoneId: event.zoneId,
        detectedAt: event.detectedAt,
      },
    );
  }

  async handleIncidentStatusChanged(event: IncidentStatusChangedEvent) {
    this.logger.log(`Status changed event: ${JSON.stringify(event)}`);

    let tokens: DeviceToken[];
    let notification: { title: string; body: string };

    if (event.toStatus === 'dispatched' && event.assignedTo) {
      // Notify the assigned guard only — zone does not apply here
      tokens = await this.deviceTokensService.findByUserId(event.assignedTo);
      notification = {
        title: '📍 You have been dispatched',
        body: `Report to camera zone for incident ${event.incidentId}`,
      };
    } else {
      // Notify all users assigned to the incident's zone
      tokens = await this.getZoneUserTokens(event.zoneId);
      notification = {
        title: `Incident ${event.toStatus.replace('_', ' ').toUpperCase()}`,
        body: `Incident ${event.incidentId} — Camera ${event.cameraCode}`,
      };
    }

    if (tokens.length === 0) {
      this.logger.warn(`No device tokens found for status change in zone ${event.zoneId} — skipping push`);
      return;
    }

    await this.sendToTokens(
      tokens.map(t => t.fcmToken),
      notification,
      {
        incidentId: event.incidentId,
        type: 'incident.status_changed',
        fromStatus: event.fromStatus,
        toStatus: event.toStatus,
      },
    );
  }

  // Fetches all users assigned to a zone from user-service, then returns their device tokens
  private async getZoneUserTokens(zoneId: string): Promise<DeviceToken[]> {
    let userIds: string[];

    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.userServiceUrl}/zone-assignments/zone/${zoneId}/users`, {
            headers: { authorization: `Bearer ${this.alertServiceToken}` },
          })
          .pipe(timeout(5000)),
      );
      // Response: [{ authUserId, zoneId, profile: { ... } }, ...]
      userIds = (response.data as any[]).map((item: any) => item.authUserId);
    } catch (err: any) {
      this.logger.warn(`Could not fetch zone users for zone ${zoneId}: ${err.message}`);
      return [];
    }

    if (userIds.length === 0) {
      this.logger.warn(`Zone ${zoneId} has no assigned users`);
      return [];
    }

    return this.deviceTokensService.findByUserIds(userIds);
  }

  private async sendToTokens(
    fcmTokens: string[],
    notification: { title: string; body: string },
    data: Record<string, string>,
  ) {
    if (!this.firebaseEnabled) {
      this.logger.log(`[LOG MODE] Would send push to ${fcmTokens.length} device(s):`);
      this.logger.log(`  Title: ${notification.title}`);
      this.logger.log(`  Body:  ${notification.body}`);
      this.logger.log(`  Data:  ${JSON.stringify(data)}`);
      return;
    }

    const chunks = this.chunkArray(fcmTokens, 500);
    for (const chunk of chunks) {
      try {
        const result = await admin.messaging().sendEachForMulticast({
          tokens: chunk,
          notification,
          data,
          android: { priority: 'high' },
          apns: { payload: { aps: { sound: 'default', badge: 1 } } },
        });
        this.logger.log(`FCM sent: ${result.successCount} success, ${result.failureCount} failed`);
      } catch (err: any) {
        this.logger.error(`FCM send error: ${err.message}`);
      }
    }
  }

  private chunkArray<T>(arr: T[], size: number): T[][] {
    const chunks: T[][] = [];
    for (let i = 0; i < arr.length; i += size) {
      chunks.push(arr.slice(i, i + size));
    }
    return chunks;
  }
}

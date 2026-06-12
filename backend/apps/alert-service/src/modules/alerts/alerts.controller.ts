import { Controller, Logger } from '@nestjs/common';
import { EventPattern, Payload } from '@nestjs/microservices';
import { AlertsService } from './alerts.service';

@Controller()
export class AlertsController {
  private readonly logger = new Logger(AlertsController.name);

  constructor(private readonly alertsService: AlertsService) {}

  @EventPattern('sentinel.incident.new')
  async onIncidentNew(@Payload() event: any) {
    this.logger.log(`Received sentinel.incident.new: incidentId=${event?.incidentId}`);
    await this.alertsService.handleIncidentNew(event);
  }

  @EventPattern('sentinel.incident.status_changed')
  async onIncidentStatusChanged(@Payload() event: any) {
    this.logger.log(
      `Received sentinel.incident.status_changed: incidentId=${event?.incidentId} ${event?.fromStatus}→${event?.toStatus}`,
    );
    await this.alertsService.handleIncidentStatusChanged(event);
  }
}

import { Controller, Get } from '@nestjs/common';

// Root controller — used only for health checks
// All real logic lives in ProfilesModule and ZoneAssignmentsModule
@Controller()
export class UserServiceController {
  @Get('health')
  health() {
    return { status: 'ok', service: 'user-service' };
  }
}

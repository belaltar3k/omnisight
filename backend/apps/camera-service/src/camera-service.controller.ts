import { Controller, Get } from '@nestjs/common';

@Controller()
export class CameraServiceController {
  @Get('health')
  health() {
    return { status: 'ok', service: 'camera-service' };
  }
}

import { Controller, Get } from '@nestjs/common';

@Controller()
export class ApiGatewayController {
  @Get('health')
  health() {
    return { status: 'ok', service: 'api-gateway' };
  }
}

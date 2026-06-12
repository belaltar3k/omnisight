import { Body, Controller, Delete, HttpCode, HttpStatus, Post, Req, UseGuards } from '@nestjs/common';
import { DeviceTokensService } from './device-tokens.service';
import { RegisterTokenDto } from './dto/register-token.dto';
import { JwtAuthGuard } from '../../../../../libs/common/src/guards/jwt-auth.guard';

@Controller('device-tokens')
@UseGuards(JwtAuthGuard)
export class DeviceTokensController {
  constructor(private readonly deviceTokensService: DeviceTokensService) {}

  @Post()
  register(@Req() req: any, @Body() dto: RegisterTokenDto) {
    return this.deviceTokensService.register(req.user.sub, req.user.role, dto);
  }

  @Delete()
  @HttpCode(HttpStatus.OK)
  unregister(@Req() req: any, @Body('fcmToken') fcmToken: string) {
    return this.deviceTokensService.unregister(req.user.sub, fcmToken);
  }
}

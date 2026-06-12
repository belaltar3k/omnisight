import {
  Body,
  Controller,
  Delete,
  Get,
  Headers,
  HttpCode,
  HttpException,
  HttpStatus,
  Post,
  UseGuards,
} from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom, timeout } from 'rxjs';
import { JwtAuthGuard } from '../../../../../libs/common/src/guards/jwt-auth.guard';

@Controller('api/v1')
@UseGuards(JwtAuthGuard)
export class AlertProxyController {
  private readonly alertServiceUrl: string;

  constructor(
    private readonly httpService: HttpService,
    configService: ConfigService,
  ) {
    this.alertServiceUrl =
      configService.get<string>('ALERT_SERVICE_URL') ?? 'http://localhost:3005';
  }

  private handleError(error: any): never {
    throw new HttpException(
      error.response?.data ?? { message: 'Alert service is unavailable' },
      error.response?.status ?? 502,
    );
  }

  private authHeaders(authorization: string) {
    return { headers: { authorization } };
  }

  // POST /api/v1/device-tokens — register FCM token
  @Post('device-tokens')
  registerToken(
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    return firstValueFrom(
      this.httpService
        .post(`${this.alertServiceUrl}/device-tokens`, body, this.authHeaders(authorization))
        .pipe(timeout(5000)),
    )
      .then(r => r.data)
      .catch(e => this.handleError(e));
  }

  // DELETE /api/v1/device-tokens — unregister FCM token
  @Delete('device-tokens')
  @HttpCode(HttpStatus.OK)
  unregisterToken(
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    return firstValueFrom(
      this.httpService
        .delete(`${this.alertServiceUrl}/device-tokens`, {
          ...this.authHeaders(authorization),
          data: body,
        })
        .pipe(timeout(5000)),
    )
      .then(r => r.data)
      .catch(e => this.handleError(e));
  }
}

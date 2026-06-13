import {
  Controller,
  All,
  Req,
  Headers,
  HttpException,
  UseGuards,
} from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom, timeout } from 'rxjs';
import { JwtAuthGuard } from '../../../../../libs/common/src/guards/jwt-auth.guard';

@Controller('api/v1/analytics')
@UseGuards(JwtAuthGuard)
export class AnalyticsProxyController {
  private readonly analyticsServiceUrl: string;

  constructor(
    private readonly httpService: HttpService,
    configService: ConfigService,
  ) {
    // Default to port 3006 for the Python Analytics Service
    this.analyticsServiceUrl =
      configService.get<string>('ANALYTICS_SERVICE_URL') ?? 'http://localhost:3006';
  }

  private handleError(error: any): never {
    throw new HttpException(
      error.response?.data ?? { message: 'Analytics service is unavailable' },
      error.response?.status ?? 502,
    );
  }

  private authHeaders(authorization: string) {
    return { headers: { authorization } };
  }

  @All('*path')
  async proxyAll(
    @Req() req: any,
    @Headers('authorization') authorization: string,
  ) {
    // req.originalUrl contains the full path, e.g., /api/v1/analytics/dashboard?time=1d
    const url = `${this.analyticsServiceUrl}${req.originalUrl}`;
    
    try {
      const response = await firstValueFrom(
        this.httpService.request({
          method: req.method,
          url,
          data: req.body,
          ...this.authHeaders(authorization),
          timeout: 10000,
        }),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }
}

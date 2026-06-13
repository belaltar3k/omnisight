import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';

import { ApiGatewayController } from './api-gateway.controller';
import { ApiGatewayService } from './api-gateway.service';
import { AuthProxyModule } from './modules/auth-proxy/auth-proxy.module';
import { CameraProxyModule } from './modules/camera-proxy/camera-proxy.module';
import { UserProxyModule } from './modules/user-proxy/user-proxy.module';
import { IncidentProxyModule } from './modules/incident-proxy/incident-proxy.module';
import { AlertProxyModule } from './modules/alert-proxy/alert-proxy.module';
import { AnalyticsProxyModule } from './modules/analytics-proxy/analytics-proxy.module';
import { JwtStrategy } from '../../../libs/common/src/strategies/jwt.strategy';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    PassportModule.register({ defaultStrategy: 'jwt' }),
    JwtModule.registerAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        secret: config.get<string>('JWT_ACCESS_SECRET'),
      }),
    }),
    AuthProxyModule,
    CameraProxyModule,
    UserProxyModule,
    IncidentProxyModule,
    AlertProxyModule,
    AnalyticsProxyModule,
  ],
  controllers: [ApiGatewayController],
  providers: [ApiGatewayService, JwtStrategy],
})
export class ApiGatewayModule {}
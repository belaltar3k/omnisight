import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { DeviceToken } from './modules/device-tokens/entities/device-token.entity';
import { DeviceTokensModule } from './modules/device-tokens/device-tokens.module';
import { AlertsModule } from './modules/alerts/alerts.module';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        type: 'postgres',
        host:     config.get('ALERT_DB_HOST', 'localhost'),
        port:     config.get<number>('ALERT_DB_PORT', 5436),
        username: config.get('ALERT_DB_USERNAME', 'sentinel'),
        password: config.get('ALERT_DB_PASSWORD', 'sentinel123'),
        database: config.get('ALERT_DB_NAME', 'sentinel_alert'),
        entities:    [DeviceToken],
        synchronize: true,
      }),
    }),
    DeviceTokensModule,
    AlertsModule,
  ],
})
export class AlertServiceModule {}

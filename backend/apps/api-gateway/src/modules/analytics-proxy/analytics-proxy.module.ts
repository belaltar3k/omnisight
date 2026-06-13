import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { ConfigModule } from '@nestjs/config';
import { AnalyticsProxyController } from './analytics-proxy.controller';

@Module({
  imports: [
    HttpModule,
    ConfigModule,
  ],
  controllers: [AnalyticsProxyController],
})
export class AnalyticsProxyModule {}

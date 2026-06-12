import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { ConfigModule } from '@nestjs/config';
import { AlertProxyController } from './alert-proxy.controller';

@Module({
  imports: [HttpModule, ConfigModule],
  controllers: [AlertProxyController],
})
export class AlertProxyModule {}

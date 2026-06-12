import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { ConfigModule } from '@nestjs/config';
import { IncidentProxyController } from './incident-proxy.controller';

@Module({
  imports: [HttpModule, ConfigModule],
  controllers: [IncidentProxyController],
})
export class IncidentProxyModule {}

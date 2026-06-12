import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { ConfigModule } from '@nestjs/config';
import { CameraProxyController } from './camera-proxy.controller';

@Module({
  imports: [
    HttpModule,
    // ✅ Added: needed so ConfigService works in CameraProxyController
    ConfigModule,
  ],
  controllers: [CameraProxyController],
})
export class CameraProxyModule {}

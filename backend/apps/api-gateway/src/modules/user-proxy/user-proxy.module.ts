import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { ConfigModule } from '@nestjs/config';
import { UserProxyController } from './user-proxy.controller';

@Module({
  imports: [
    HttpModule,
    // ✅ Added: needed so UserProxyController can inject ConfigService
    ConfigModule,
  ],
  controllers: [UserProxyController],
})
export class UserProxyModule {}

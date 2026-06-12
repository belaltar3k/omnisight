import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { ConfigModule } from '@nestjs/config';
import { AuthProxyController } from './auth-proxy.controller';

@Module({
  imports: [
    HttpModule,
    ConfigModule,
  ],
  controllers: [AuthProxyController],
})
export class AuthProxyModule {}
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ConfigModule } from '@nestjs/config';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';
import { ConfigService } from '@nestjs/config';
import { DeviceToken } from './entities/device-token.entity';
import { DeviceTokensService } from './device-tokens.service';
import { DeviceTokensController } from './device-tokens.controller';
import { JwtStrategy } from '../../../../../libs/common/src/strategies/jwt.strategy';

@Module({
  imports: [
    TypeOrmModule.forFeature([DeviceToken]),
    ConfigModule,
    PassportModule.register({ defaultStrategy: 'jwt' }),
    JwtModule.registerAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        secret: config.get<string>('JWT_ACCESS_SECRET'),
      }),
    }),
  ],
  controllers: [DeviceTokensController],
  providers: [DeviceTokensService, JwtStrategy],
  exports: [DeviceTokensService],
})
export class DeviceTokensModule {}

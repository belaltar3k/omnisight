import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';

import { ZonesModule } from './modules/zones/zones.module';
import { EdgeNodesModule } from './modules/edge-nodes/edge-nodes.module';
import { CamerasModule } from './modules/cameras/cameras.module';
import { CameraServiceController } from './camera-service.controller';
import { JwtStrategy } from '../../../libs/common/src/strategies/jwt.strategy';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),

    TypeOrmModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (configService: ConfigService) => ({
        type: 'postgres',
        host: configService.get<string>('CAMERA_DB_HOST'),
        port: Number(configService.get<string>('CAMERA_DB_PORT')),
        username: configService.get<string>('CAMERA_DB_USERNAME'),
        password: configService.get<string>('CAMERA_DB_PASSWORD'),
        database: configService.get<string>('CAMERA_DB_NAME'),
        autoLoadEntities: true,
        synchronize: true,
      }),
    }),

    // ✅ Required so JwtAuthGuard knows which strategy to use
    PassportModule.register({ defaultStrategy: 'jwt' }),

    // ✅ Required so JwtStrategy can verify tokens
    JwtModule.registerAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        secret: config.get<string>('JWT_ACCESS_SECRET'),
      }),
    }),

    // ✅ Fixed: removed duplicate ZonesModule and EdgeNodesModule
    ZonesModule,
    EdgeNodesModule,
    CamerasModule,
  ],
  controllers: [CameraServiceController],
  // ✅ JwtStrategy must be a provider so Passport registers the 'jwt' strategy
  providers: [JwtStrategy],
})
export class CameraServiceModule {}

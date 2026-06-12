import { Module } from '@nestjs/common';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { TypeOrmModule } from '@nestjs/typeorm';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport';

import { IncidentsModule } from './modules/incidents/incidents.module';
import { JwtStrategy } from '../../../libs/common/src/strategies/jwt.strategy';

@Module({
  imports: [
    ConfigModule.forRoot({ isGlobal: true }),

    TypeOrmModule.forRootAsync({
      inject: [ConfigService],
      useFactory: (configService: ConfigService) => ({
        type: 'postgres',
        host: configService.get<string>('INCIDENT_DB_HOST'),
        port: Number(configService.get<string>('INCIDENT_DB_PORT')),
        username: configService.get<string>('INCIDENT_DB_USERNAME'),
        password: configService.get<string>('INCIDENT_DB_PASSWORD'),
        database: configService.get<string>('INCIDENT_DB_NAME'),
        autoLoadEntities: true,
        synchronize: true,
      }),
    }),

    PassportModule.register({ defaultStrategy: 'jwt' }),

    JwtModule.registerAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        secret: config.get<string>('JWT_ACCESS_SECRET'),
      }),
    }),

    IncidentsModule,
  ],
  providers: [JwtStrategy],
})
export class IncidentServiceModule {}

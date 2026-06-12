import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { HttpModule } from '@nestjs/axios';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { JwtModule } from '@nestjs/jwt';

import { ZoneAssignment } from './entities/zone-assignment.entity';
import { UserProfile } from '../profiles/entities/user-profile.entity';
import { ZoneAssignmentsService } from './zone-assignments.service';
import { ZoneAssignmentsController } from './zone-assignments.controller';

@Module({
  imports: [
    TypeOrmModule.forFeature([ZoneAssignment, UserProfile]),
    HttpModule,
    ConfigModule,
    JwtModule.registerAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => ({
        secret: config.get<string>('JWT_ACCESS_SECRET'),
      }),
    }),
  ],
  controllers: [ZoneAssignmentsController],
  providers: [ZoneAssignmentsService],
  exports: [ZoneAssignmentsService],
})
export class ZoneAssignmentsModule {}

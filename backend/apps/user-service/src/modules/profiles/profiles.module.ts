import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { HttpModule } from '@nestjs/axios';
import { ConfigModule } from '@nestjs/config';

import { UserProfile } from './entities/user-profile.entity';
import { ZoneAssignment } from '../zone-assignments/entities/zone-assignment.entity';
import { ProfilesService } from './profiles.service';
import { ProfilesController } from './profiles.controller';

@Module({
  imports: [
    TypeOrmModule.forFeature([UserProfile, ZoneAssignment]),
    HttpModule,
    // ✅ Added: needed so ProfilesService can inject ConfigService for env URLs
    ConfigModule,
  ],
  controllers: [ProfilesController],
  providers: [ProfilesService],
  exports: [ProfilesService],
})
export class ProfilesModule {}

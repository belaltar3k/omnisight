import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Zone } from './entities/zone.entity';
import { ZonesService } from './zones.service';
import { ZonesController } from './zones.controller';
import { Camera } from '../cameras/entities/camera.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Zone,Camera])],
  controllers: [ZonesController],
  providers: [ZonesService],
  exports: [ZonesService],
})
export class ZonesModule {}
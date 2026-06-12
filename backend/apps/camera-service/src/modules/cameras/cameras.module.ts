import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { Camera } from './entities/camera.entity';
import { CamerasController } from './cameras.controller';
import { CamerasService } from './cameras.service';
import { Zone } from '../zones/entities/zone.entity';
import { EdgeNode } from '../edge-nodes/entities/edge-node.entity';

@Module({
  imports: [TypeOrmModule.forFeature([Camera, Zone, EdgeNode])],
  controllers: [CamerasController],
  providers: [CamerasService],
  exports: [CamerasService],
})
export class CamerasModule {}
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { EdgeNode } from './entities/edge-node.entity';
import { EdgeNodesService } from './edge-nodes.service';
import { EdgeNodesController } from './edge-nodes.controller';
import { Camera } from '../cameras/entities/camera.entity';

@Module({
  imports: [TypeOrmModule.forFeature([EdgeNode, Camera])],
  controllers: [EdgeNodesController],
  providers: [EdgeNodesService],
  exports: [EdgeNodesService],
})
export class EdgeNodesModule {}
import {
  Column,
  CreateDateColumn,
  Entity,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';

import { CameraStatus } from '../../../../../../libs/common/enums/camera-status.enum';
import { Zone } from '../../zones/entities/zone.entity';
import { EdgeNode } from '../../edge-nodes/entities/edge-node.entity';

@Entity('cameras')
export class Camera {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column()
  name!: string;

  @Column({ unique: true })
  code!: string;

  @Column({ name: 'rtsp_url' })
  rtspUrl!: string;

  @Column({
    type: 'enum',
    enum: CameraStatus,
    default: CameraStatus.OFFLINE,
  })
  status!: CameraStatus;

  @Column({ name: 'target_fps', default: 30 })
  targetFps!: number;

  @Column({ name: 'resolution_width', default: 1920 })
  resolutionWidth!: number;

  @Column({ name: 'resolution_height', default: 1080 })
  resolutionHeight!: number;

  @Column({ name: 'zone_id' })
  zoneId!: string;

  @ManyToOne(() => Zone)
  @JoinColumn({ name: 'zone_id' })
  zone!: Zone;

  @Column({ name: 'edge_node_id' })
  edgeNodeId!: string;

  @ManyToOne(() => EdgeNode)
  @JoinColumn({ name: 'edge_node_id' })
  edgeNode!: EdgeNode;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt!: Date;
}
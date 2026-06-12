import {
  Column,
  CreateDateColumn,
  Entity,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';
import { EdgeNodeStatus } from '../../../../../../libs/common/enums/edge-node-status.enum';

@Entity('edge_nodes')
export class EdgeNode {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column()
  name!: string;

  @Column({ unique: true })
  code!: string;

  @Column({ name: 'ip_address' })
  ipAddress!: string;

  @Column({
    type: 'enum',
    enum: EdgeNodeStatus,
    default: EdgeNodeStatus.ACTIVE,
  })
  status!: EdgeNodeStatus;

  @Column({ name: 'max_cameras', default: 8 })
  maxCameras!: number;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt!: Date;
}
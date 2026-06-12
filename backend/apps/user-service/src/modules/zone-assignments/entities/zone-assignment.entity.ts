import {
  Column,
  CreateDateColumn,
  Entity,
  PrimaryGeneratedColumn,
} from 'typeorm';

@Entity('zone_assignments')
export class ZoneAssignment {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'auth_user_id' })
  authUserId!: string;

  @Column({ name: 'zone_id' })
  zoneId!: string;

  @Column({ nullable: true })
  notes?: string;

  @CreateDateColumn({ name: 'assigned_at' })
  assignedAt!: Date;
}
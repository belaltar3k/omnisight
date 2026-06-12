import {
  Column,
  CreateDateColumn,
  Entity,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
} from 'typeorm';
import { Incident } from './incident.entity';

@Entity('incident_timeline')
export class IncidentTimeline {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'incident_id' })
  incidentId!: string;

  @ManyToOne(() => Incident, (incident) => incident.timeline)
  @JoinColumn({ name: 'incident_id' })
  incident!: Incident;

  @Column()
  action!: string;

  @Column({ name: 'performed_by', nullable: true })
  performedBy!: string;

  @Column({ name: 'from_status', nullable: true })
  fromStatus!: string;

  @Column({ name: 'to_status', nullable: true })
  toStatus!: string;

  @Column({ nullable: true })
  notes!: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;
}

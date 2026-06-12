import {
  Column,
  CreateDateColumn,
  Entity,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';

@Entity('user_profiles')
export class UserProfile {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'auth_user_id', unique: true })
  authUserId!: string;

  @Column({ name: 'full_name' })
  fullName!: string;

  @Column({ unique: true, nullable: true })
  employeeCode?: string;

  @Column({ nullable: true })
  phone?: string;

  @Column({ nullable: true })
  address?: string;

  @Column({ name: 'avatar_url', nullable: true })
  avatarUrl?: string;

  @Column({ name: 'job_title', nullable: true })
  jobTitle?: string;

  @Column({ nullable: true })
  department?: string;

  @Column({ nullable: true })
  shiftName?: string;

  @Column({ nullable: true })
  emergencyContact?: string;

  @Column({ nullable: true })
  emergencyPhone?: string;

  @Column({ default: true })
  isActive!: boolean;

  @CreateDateColumn()
  createdAt!: Date;

  @UpdateDateColumn()
  updatedAt!: Date;
  
}
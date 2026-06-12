import { IsNotEmpty, IsOptional, IsString } from 'class-validator';

export class AssignIncidentDto {
  @IsString()
  @IsNotEmpty()
  assignedTo!: string;

  @IsOptional()
  @IsString()
  notes?: string;
}

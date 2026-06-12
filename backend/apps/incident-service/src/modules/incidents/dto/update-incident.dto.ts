import { IsEnum, IsOptional, IsString } from 'class-validator';
import { CrimeType, IncidentPriority } from '../../entities/incident.entity';

export class UpdateIncidentDto {
  @IsOptional()
  @IsEnum(CrimeType)
  crimeType?: CrimeType;

  @IsOptional()
  @IsEnum(IncidentPriority)
  priority?: IncidentPriority;

  @IsOptional()
  @IsString()
  videoUrl?: string;

  @IsOptional()
  @IsString()
  thumbnailUrl?: string;

  @IsOptional()
  @IsString()
  modelVersion?: string;
}

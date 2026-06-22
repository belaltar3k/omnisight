import { IsEnum, IsNotEmpty, IsNumber, IsObject, IsOptional, IsString, Max, Min } from 'class-validator';
import { CrimeType } from '../../entities/incident.entity';

export class EdgeClassifyDto {
  @IsString()
  @IsNotEmpty()
  trackId!: string;

  @IsEnum(CrimeType, { message: `crimeType must be one of: ${Object.values(CrimeType).join(', ')}` })
  crimeType!: CrimeType;

  @IsNumber()
  @Min(0)
  @Max(1)
  confidence!: number;

  @IsOptional()
  @IsString()
  videoUrl?: string;

  @IsOptional()
  @IsObject()
  vlmVerification?: {
    status: 'completed';
    verifiedCrimeType?: string;
    caption?: string;
    anomalyScoreVlm?: string;
    observedEvents?: string[];
    anomalyEvidence?: string[];
    peopleCount?: number;
    completedAt?: string;
  };
}

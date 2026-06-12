import { Type } from 'class-transformer';
import {
  IsArray, IsDateString, IsNotEmpty, IsNumber,
  IsObject, IsOptional, IsString, Max, Min, ValidateNested,
} from 'class-validator';

export class DetectionItemDto {
  @IsString()
  @IsNotEmpty()
  cameraCode!: string;

  @IsString()
  @IsNotEmpty()
  trackId!: string;

  @IsString()
  @IsNotEmpty()
  crimeType!: string;

  @IsNumber()
  @Min(0)
  @Max(1)
  confidence!: number;

  @IsDateString()
  detectedAt!: string;

  @IsOptional()
  @IsString()
  videoUrl?: string;

  @IsOptional()
  @IsString()
  thumbnailUrl?: string;

  @IsOptional()
  @IsString()
  modelVersion?: string;

  @IsOptional()
  @IsObject()
  aiMetadata?: { keypoints?: any[]; boundingBoxes?: any[]; raw?: any };
}

export class EdgeSyncDto {
  @IsString()
  @IsNotEmpty()
  edgeNodeCode!: string;

  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => DetectionItemDto)
  detections!: DetectionItemDto[];
}
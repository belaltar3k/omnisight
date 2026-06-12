import { IsEnum, IsNotEmpty, IsNumber, IsOptional, IsString, Min } from 'class-validator';
import { CameraStatus } from '../../../../../../libs/common/enums/camera-status.enum';

export class CreateCameraDto {
  @IsString()
  @IsNotEmpty()
  name!: string;

  @IsString()
  @IsNotEmpty()
  code!: string;

  @IsString()
  @IsNotEmpty()
  rtspUrl!: string;

  @IsString()
  @IsNotEmpty()
  zoneId!: string;

  @IsString()
  @IsNotEmpty()
  edgeNodeId!: string;

  @IsOptional()
  @IsEnum(CameraStatus)
  status?: CameraStatus;

  @IsOptional()
  @IsNumber()
  @Min(1)
  targetFps?: number;

  @IsOptional()
  @IsNumber()
  resolutionWidth?: number;

  @IsOptional()
  @IsNumber()
  resolutionHeight?: number;
}
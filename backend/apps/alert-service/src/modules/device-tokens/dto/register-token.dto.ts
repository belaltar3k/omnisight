import { IsIn, IsNotEmpty, IsOptional, IsString } from 'class-validator';

export class RegisterTokenDto {
  @IsString()
  @IsNotEmpty()
  fcmToken!: string;

  @IsOptional()
  @IsIn(['ios', 'android', 'web'])
  deviceType?: string;
}

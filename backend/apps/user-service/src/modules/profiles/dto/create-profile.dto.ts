import { IsNotEmpty, IsOptional, IsString } from 'class-validator';

export class CreateProfileDto {
  @IsString()
  @IsNotEmpty()
  authUserId!: string;

  @IsString()
  @IsNotEmpty()
  fullName!: string;

  @IsOptional()
  @IsString()
  phone?: string;

  @IsOptional()
  @IsString()
  avatarUrl?: string;

  @IsOptional()
  @IsString()
  jobTitle?: string;

  @IsOptional()
  @IsString()
  department?: string;

    @IsOptional()  
    @IsString()
    shiftName?: string;
    
  @IsOptional()
  @IsString()
  emergencyContact?: string;

    @IsOptional()
    @IsString()
    emergencyPhone?: string;

    @IsOptional()
    @IsString()
    employeeCode?: string;

    @IsOptional()
    @IsString()
    address?: string;   

    @IsOptional()
    @IsString()
    isActive?: boolean;    

}
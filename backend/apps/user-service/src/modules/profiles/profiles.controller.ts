import {
  Body,
  Controller,
  Get,
  Param,
  Patch,
  Post,
  Req,
  UseGuards,
} from '@nestjs/common';
import { Headers, UnauthorizedException } from '@nestjs/common';
import { ProfilesService } from './profiles.service';
import { CreateProfileDto } from './dto/create-profile.dto';
import { UpdateProfileDto } from './dto/update-profile.dto';
import { JwtAuthGuard } from '../../../../../libs/common/src/guards/jwt-auth.guard';
import { RolesGuard } from '../../../../../libs/common/src/guards/roles.guards';
import { Roles } from '../../../../../libs/common/src/decorators/roles.decorator';
import { UserRole } from '../../../../../libs/common/enums/user.role.enum';

@Controller('profiles')
export class ProfilesController {
  constructor(private readonly profilesService: ProfilesService) {}

  // ─── Create ──────────────────────────────────────────────────────────────
  // ✅ Only admins or supervisors can create profiles (internal operation)
  @Post()
create(
  @Body() dto: CreateProfileDto,
  @Headers('x-internal-secret') secret: string,
) {
  if (secret !== process.env.INTERNAL_SECRET) {
    throw new UnauthorizedException();
  }
  return this.profilesService.create(dto);
}

  // ─── List All ────────────────────────────────────────────────────────────
  // ✅ Admin only — exposes all user personal data
  @Get()
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN)
  findAll() {
    return this.profilesService.findAll();
  }

  // ─── Full Profile (with zone assignments) ────────────────────────────────
  // ✅ IMPORTANT: /full route must stay ABOVE /:authUserId to avoid being caught by it
  @Get('auth/:authUserId/full')
  @UseGuards(JwtAuthGuard)
  findFullProfile(@Param('authUserId') authUserId: string, @Req() req: any) {
    this.assertSelfOrAdmin(req, authUserId);
    return this.profilesService.findFullProfile(authUserId);
  }

  // ─── Get by authUserId ───────────────────────────────────────────────────
  @Get('auth/:authUserId')
  @UseGuards(JwtAuthGuard)
  findByAuthUserId(
    @Param('authUserId') authUserId: string,
    @Req() req: any,
  ) {
    this.assertSelfOrAdmin(req, authUserId);
    return this.profilesService.findByAuthUserId(authUserId);
  }

  // ─── Update ──────────────────────────────────────────────────────────────
  // ✅ New: users can update their own profile; admins can update anyone's
  @Patch('auth/:authUserId')
  @UseGuards(JwtAuthGuard)
  update(
    @Param('authUserId') authUserId: string,
    @Body() dto: UpdateProfileDto,
    @Req() req: any,
  ) {
    this.assertSelfOrAdmin(req, authUserId);
    return this.profilesService.update(authUserId, dto);
  }

  // ─── Helper ──────────────────────────────────────────────────────────────
  // ✅ Enforces: only the profile owner OR an admin can access/modify
  private assertSelfOrAdmin(req: any, authUserId: string) {
    const user = req.user;
    const isAdmin = user?.role === UserRole.ADMIN;
    const isSelf = user?.sub === authUserId;

    if (!isAdmin && !isSelf) {
      const { ForbiddenException } = require('@nestjs/common');
      throw new ForbiddenException('You can only access your own profile');
    }
  }
}

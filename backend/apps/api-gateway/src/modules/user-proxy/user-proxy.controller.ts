import {
  Body,
  Controller,
  Delete,
  Get,
  Headers,
  HttpException,
  Param,
  Patch,
  Post,
  Req,
  UseGuards,
} from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom, timeout } from 'rxjs';
import { JwtAuthGuard } from '../../../../../libs/common/src/guards/jwt-auth.guard';
import { RolesGuard } from '../../../../../libs/common/src/guards/roles.guards';
import { Roles } from '../../../../../libs/common/src/decorators/roles.decorator';
import { UserRole } from '../../../../../libs/common/enums/user.role.enum';

@Controller('api/v1')
@UseGuards(JwtAuthGuard)
export class UserProxyController {
  private readonly userServiceUrl: string;
  private readonly internalSecret: string;

  constructor(
    private readonly httpService: HttpService,
    configService: ConfigService,
  ) {
    this.userServiceUrl =
      configService.get<string>('USER_SERVICE_URL') ?? 'http://localhost:3004';
    this.internalSecret = configService.get<string>('INTERNAL_SECRET') ?? '';
  }

  private handleError(error: any): never {
    throw new HttpException(
      error.response?.data ?? { message: 'User service is unavailable' },
      error.response?.status ?? 502,
    );
  }

  private authHeaders(authorization: string) {
    return { headers: { authorization } };
  }

  // ══════════════════════════════════════════════════════════════════════════
  // PROFILES
  // ══════════════════════════════════════════════════════════════════════════

  // POST /api/v1/profiles
  // Gateway validates JWT role, then calls user service with internal secret
  @Post('profiles')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async createProfile(@Body() body: any) {
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .post(`${this.userServiceUrl}/profiles`, body, {
            headers: { 'x-internal-secret': this.internalSecret },
          })
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/profiles
  @Get('profiles')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  async getProfiles(@Headers('authorization') authorization: string) {
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .get(`${this.userServiceUrl}/profiles`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/profiles/auth/:authUserId/full
  // IMPORTANT: must stay ABOVE /auth/:authUserId to avoid route conflict
  @Get('profiles/auth/:authUserId/full')
  async getFullProfile(
    @Param('authUserId') authUserId: string,
    @Req() req: any,
    @Headers('authorization') authorization: string,
  ) {
    this.assertSelfOrAdmin(req, authUserId);
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .get(
            `${this.userServiceUrl}/profiles/auth/${authUserId}/full`,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/profiles/auth/:authUserId
  @Get('profiles/auth/:authUserId')
  async getProfileByAuthUserId(
    @Param('authUserId') authUserId: string,
    @Req() req: any,
    @Headers('authorization') authorization: string,
  ) {
    this.assertSelfOrAdmin(req, authUserId);
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .get(
            `${this.userServiceUrl}/profiles/auth/${authUserId}`,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // PATCH /api/v1/profiles/auth/:authUserId
  @Patch('profiles/auth/:authUserId')
  async updateProfile(
    @Param('authUserId') authUserId: string,
    @Body() body: any,
    @Req() req: any,
    @Headers('authorization') authorization: string,
  ) {
    this.assertSelfOrAdmin(req, authUserId);
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .patch(
            `${this.userServiceUrl}/profiles/auth/${authUserId}`,
            body,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // DELETE /api/v1/profiles/auth/:authUserId
  @Delete('profiles/auth/:authUserId')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  async deleteProfile(
    @Param('authUserId') authUserId: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .delete(
            `${this.userServiceUrl}/profiles/auth/${authUserId}`,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // ZONE ASSIGNMENTS
  // ══════════════════════════════════════════════════════════════════════════

  // POST /api/v1/zone-assignments
  @Post('zone-assignments')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async createZoneAssignment(
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .post(
            `${this.userServiceUrl}/zone-assignments`,
            body,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/zone-assignments
  @Get('zone-assignments')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  async getZoneAssignments(@Headers('authorization') authorization: string) {
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .get(
            `${this.userServiceUrl}/zone-assignments`,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/zone-assignments/user/:authUserId
  @Get('zone-assignments/user/:authUserId')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async getAssignmentsByUser(
    @Param('authUserId') authUserId: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .get(
            `${this.userServiceUrl}/zone-assignments/user/${authUserId}`,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/zone-assignments/zone/:zoneId/users
  // IMPORTANT: must stay ABOVE /zone/:zoneId to avoid route conflict
  @Get('zone-assignments/zone/:zoneId/users')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async getUsersByZone(
    @Param('zoneId') zoneId: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .get(
            `${this.userServiceUrl}/zone-assignments/zone/${zoneId}/users`,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/zone-assignments/zone/:zoneId
  @Get('zone-assignments/zone/:zoneId')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async getAssignmentsByZone(
    @Param('zoneId') zoneId: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .get(
            `${this.userServiceUrl}/zone-assignments/zone/${zoneId}`,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // PATCH /api/v1/zone-assignments/:id/reassign
  @Patch('zone-assignments/:id/reassign')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async reassignZone(
    @Param('id') id: string,
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .patch(
            `${this.userServiceUrl}/zone-assignments/${id}/reassign`,
            body,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // DELETE /api/v1/zone-assignments/user/:authUserId/zone/:zoneId
  // IMPORTANT: must stay ABOVE /:id to avoid route conflict
  @Delete('zone-assignments/user/:authUserId/zone/:zoneId')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async removeAssignmentByUserAndZone(
    @Param('authUserId') authUserId: string,
    @Param('zoneId') zoneId: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .delete(
            `${this.userServiceUrl}/zone-assignments/user/${authUserId}/zone/${zoneId}`,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // DELETE /api/v1/zone-assignments/:id
  @Delete('zone-assignments/:id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async removeAssignment(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response: any = await firstValueFrom(
        this.httpService
          .delete(
            `${this.userServiceUrl}/zone-assignments/${id}`,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

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

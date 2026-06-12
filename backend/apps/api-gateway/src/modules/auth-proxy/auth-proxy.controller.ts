import {
  Body,
  Controller,
  Post,
  Get,
  HttpException,
  Req,
  UseGuards,
} from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom, timeout } from 'rxjs';
import { JwtAuthGuard } from '../../../../../libs/common/src/guards/jwt-auth.guard';

@Controller('api/v1')
export class AuthProxyController {
  private readonly authServiceUrl: string;
  private readonly userServiceUrl: string;

constructor(
  private readonly httpService: HttpService,
  private readonly configService: ConfigService,  
) {
  this.authServiceUrl = configService.get<string>('AUTH_SERVICE_URL') ?? 'http://localhost:3001';
  this.userServiceUrl = configService.get<string>('USER_SERVICE_URL') ?? 'http://localhost:3004';
}

  // ─── Register (with rollback) ──────────────────────────────────────────────
  @Post('auth/register')
  async register(@Body() dto: any) {
    let authUser: any = null; 

    // ── Step 1: create auth account ──────────────────────────────────────────
    try {
      const authResponse = await firstValueFrom(
        this.httpService
          .post(`${this.authServiceUrl}/auth/register`, {
            email:    dto.email,
            password: dto.password,
            fullName: dto.fullName,
            role:     dto.role,
          })
          .pipe(timeout(5000)),
      );
      authUser = authResponse.data; // ✅ only assigned on success
    } catch (error: any) {
      // Step 1 failed — nothing was created, nothing to rollback
      // Just forward the error to the client (409, 400, etc.)
      throw new HttpException(
        error.response?.data ?? { message: 'Registration failed' },
        error.response?.status ?? 502,
      );
    }

    // ── Step 2: create profile in user-service ───────────────────────────────
    try {
      // auth-proxy.controller.ts — Step 2
await firstValueFrom(
  this.httpService
    .post(
      `${this.userServiceUrl}/profiles`,
      {
        authUserId:       authUser.user.id,
        fullName:         dto.fullName,
        phone:            dto.phone,
        avatarUrl:        dto.avatarUrl,
        jobTitle:         dto.jobTitle,
        department:       dto.department,
        shiftName:        dto.shiftName,
        emergencyContact: dto.emergencyContact,
        emergencyPhone:   dto.emergencyPhone,
        employeeCode:     dto.employeeCode,
        address:          dto.address,
      },
      {
        headers: {
          'x-internal-secret': this.configService.get('INTERNAL_SECRET'),
        },
      }, 
    )
    .pipe(timeout(5000)),
);
    } catch (error: any) {
      // ✅ Step 2 failed AND Step 1 succeeded → rollback the auth account
      // authUser is guaranteed non-null here because Step 1 passed
      try {
        await firstValueFrom(
          this.httpService
            .delete(`${this.authServiceUrl}/auth/users/${authUser.user.id}/internal`)
            .pipe(timeout(5000)),
        );
      } catch {
        // Rollback itself failed — this is a real orphan, needs manual fix
        console.error(
          `CRITICAL: orphan auth account needs manual cleanup → id: ${authUser.user.id}`,
        );
      }
      throw new HttpException(
        { message: 'Registration failed, please try again' },
        502,
      );
    }

    // ── Both succeeded ───────────────────────────────────────────────────────
    return {
      success: true,
      message: 'Account created successfully',
      user: authUser.user,
    };
  }

  // ─── Login ─────────────────────────────────────────────────────────────────
  @Post('auth/login')
  async login(@Body() body: any) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.authServiceUrl}/auth/login`, body)
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      throw new HttpException(
        error.response?.data ?? { message: 'Auth service error' },
        error.response?.status ?? 502,
      );
    }
  }

  // ─── Refresh Token ─────────────────────────────────────────────────────────
  @Post('auth/refresh')
  async refresh(@Body() body: any) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.authServiceUrl}/auth/refresh`, body)
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      throw new HttpException(
        error.response?.data ?? { message: 'Auth service error' },
        error.response?.status ?? 502,
      );
    }
  }

  // ─── Logout ────────────────────────────────────────────────────────────────
  @Post('auth/logout')
  async logout(@Body() body: any) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.authServiceUrl}/auth/logout`, body)
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      throw new HttpException(
        error.response?.data ?? { message: 'Auth service error' },
        error.response?.status ?? 502,
      );
    }
  }

  // ─── Forgot Password ───────────────────────────────────────────────────────
  @Post('auth/forgot-password')
  async forgotPassword(@Body() body: any) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.authServiceUrl}/auth/forgot-password`, body)
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      throw new HttpException(
        error.response?.data ?? { message: 'Auth service error' },
        error.response?.status ?? 502,
      );
    }
  }

  // ─── Reset Password ────────────────────────────────────────────────────────
  @Post('auth/reset-password')
  async resetPassword(@Body() body: any) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.authServiceUrl}/auth/reset-password`, body)
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      throw new HttpException(
        error.response?.data ?? { message: 'Auth service error' },
        error.response?.status ?? 502,
      );
    }
  }

  // ─── Get Me ────────────────────────────────────────────────────────────────
  @Get('auth/me')
  @UseGuards(JwtAuthGuard)
  getMe(@Req() req: any) {
    return req.user;
  }
}
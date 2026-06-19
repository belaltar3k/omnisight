import {
  ConflictException,
  Injectable,
  UnauthorizedException,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { UsersService } from '../users/users.service';
import { RegisterDto } from './dto/register.dto';
import * as bcrypt from 'bcrypt';
import { JwtService } from '@nestjs/jwt';
import { LoginDto } from './dto/login.dto';
import { RefreshDto } from './dto/refresh.dto';
import { TokensService } from '../tokens/tokens.service';
import { LogoutDto } from './dto/logout.dto';
import { ForgotPasswordDto } from './dto/forgot-password.dto';
import { ResetPasswordDto } from './dto/reset-password.dto';
import { NotFoundException } from '@nestjs/common';
interface AuthJwtPayload {
  sub: string;
  email: string;
}

@Injectable()
export class AuthService {
  private readonly refreshTokenSecret: string;

  constructor(
    private readonly usersService: UsersService,
    private readonly jwtService: JwtService,
    private readonly tokensService: TokensService,
    configService: ConfigService,
  ) {
    const accessTokenSecret = configService.get<string>('JWT_ACCESS_SECRET');
    const refreshTokenSecret = configService.get<string>('JWT_REFRESH_SECRET');

    if (!accessTokenSecret) {
      throw new Error('JWT_ACCESS_SECRET is missing');
    }

    this.refreshTokenSecret = refreshTokenSecret || accessTokenSecret;
  }

  async register(dto: RegisterDto) {
    const existingUser = await this.usersService.findByEmail(dto.email);

    if (existingUser) {
      throw new ConflictException('Email already exists');
    }

    const passwordHash = await bcrypt.hash(dto.password, 10);

    // Employee code is server-generated, never accepted from the client.
    const employeeCode = await this.usersService.generateUniqueEmployeeCode();

    const user = await this.usersService.create({
      fullName: dto.fullName,
      email: dto.email,
      passwordHash,
      role: dto.role,
      employeeCode,
    });

    return {
      message: 'User registered successfully',
      user: {
        id: user.id,
        fullName: user.fullName,
        email: user.email,
        employeeCode: user.employeeCode,
        role: user.role,
        status: user.status,
      },
    };
  }

  async login(dto: LoginDto) {
    // identifier is either an email (contains "@") or an employee code.
    const user = dto.identifier.includes('@')
      ? await this.usersService.findByEmail(dto.identifier)
      : await this.usersService.findByEmployeeCode(dto.identifier);

    if (!user) {
      throw new UnauthorizedException('Invalid credentials');
    }

    const isMatch = await bcrypt.compare(dto.password, user.passwordHash);

    if (!isMatch) {
      throw new UnauthorizedException('Invalid credentials');
    }

    const payload = {
  sub: user.id,
  email: user.email,
  role: user.role,
};

    const tokens = await this.issueTokens(payload);

    await this.tokensService.saveRefreshToken(user.id, tokens.refreshToken);

    return {
      ...tokens,
      user: {
        id: user.id,
        fullName: user.fullName,
        email: user.email,
        employeeCode: user.employeeCode,
        role: user.role,
        status: user.status,
      },
    };
  }

  async getUserById(id: string) {
  const user = await this.usersService.findById(id);

  if (!user) {
    throw new NotFoundException('Auth user not found');
  }

  return {
    id: user.id,
    email: user.email,
    role: user.role,
    status: user.status,
  };
}
  async refresh(dto: RefreshDto) {
    try {
      const payload = await this.verifyRefreshToken(dto.refreshToken);

      const savedToken = await this.tokensService.validateRefreshToken(
        payload.sub,
        dto.refreshToken,
      );

      if (!savedToken) {
        throw new UnauthorizedException('Invalid refresh token');
      }

      const tokens = await this.issueTokens({
        sub: payload.sub,
        email: payload.email,
      });

      await this.tokensService.revokeRefreshToken(savedToken.id);
      await this.tokensService.saveRefreshToken(
        payload.sub,
        tokens.refreshToken,
      );

      return tokens;
    } catch {
      throw new UnauthorizedException('Invalid refresh token');
    }
  }

  async logout(dto: LogoutDto) {
    try {
      const payload = await this.verifyRefreshToken(dto.refreshToken);

      const savedToken = await this.tokensService.validateRefreshToken(
        payload.sub,
        dto.refreshToken,
      );

      if (savedToken) {
        await this.tokensService.revokeRefreshToken(savedToken.id);
      }

      return {
        message: 'Logged out successfully',
      };
    } catch {
      throw new UnauthorizedException('Invalid refresh token');
    }
  }

  private async issueTokens(payload: AuthJwtPayload) {
    const [accessToken, refreshToken] = await Promise.all([
      this.jwtService.signAsync(payload),
      this.jwtService.signAsync(payload, {
        expiresIn: '7d',
        secret: this.refreshTokenSecret,
      }),
    ]);

    return {
      accessToken,
      refreshToken,
    };
  }

  private verifyRefreshToken(refreshToken: string) {
    return this.jwtService.verifyAsync<AuthJwtPayload>(refreshToken, {
      secret: this.refreshTokenSecret,
    });
  }

  async forgotPassword(dto: ForgotPasswordDto) {
  const user = await this.usersService.findByEmail(dto.email);

  if (!user) {
    return {
      message: 'If this email exists, a reset token has been generated',
    };
  }

  const resetToken = await this.tokensService.createPasswordResetToken(user.id);

  return {
    message: 'Password reset token generated',
    resetToken, 
  };
}

async resetPassword(dto: ResetPasswordDto) {
  const user = await this.usersService.findByEmail(dto.email);

  if (!user) {
    throw new UnauthorizedException('Invalid reset token');
  }

  const savedToken = await this.tokensService.validatePasswordResetToken(
    user.id,
    dto.token,
  );

  if (!savedToken) {
    throw new UnauthorizedException('Invalid reset token');
  }

  const passwordHash = await bcrypt.hash(dto.newPassword, 10);

  await this.usersService.updatePassword(user.id, passwordHash);

  await this.tokensService.markPasswordResetTokenAsUsed(savedToken.id);

  await this.tokensService.revokeAllUserTokens(user.id);

  return {
    message: 'Password reset successfully',
  };
}

async deleteUser(id: string) {
  const user = await this.usersService.findById(id);
  
  if (!user) {
    throw new NotFoundException('User not found');
  }

  await this.usersService.delete(id);
  await this.tokensService.revokeAllUserTokens(id);

  return {
    message: 'User deleted successfully',
  };

}
}
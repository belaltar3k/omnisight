import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { RefreshToken } from './entities/refresh-token.entity';
import { Repository } from 'typeorm';
import { PasswordResetToken } from './entities/password-reset-token.entity';
import { randomBytes } from 'crypto';
import * as bcrypt from 'bcrypt';

@Injectable()
export class TokensService {
  constructor(
  @InjectRepository(RefreshToken)
  private readonly refreshTokenRepo: Repository<RefreshToken>,

  @InjectRepository(PasswordResetToken)
  private readonly passwordResetRepo: Repository<PasswordResetToken>,
) {}

  async saveRefreshToken(userId: string, refreshToken: string) {
    const tokenHash = await bcrypt.hash(refreshToken, 10);

    const expiresAt = new Date();
    expiresAt.setDate(expiresAt.getDate() + 7);

    const token = this.refreshTokenRepo.create({
      userId,
      tokenHash,
      expiresAt,
    });

    return this.refreshTokenRepo.save(token);
  }

  async validateRefreshToken(userId: string, refreshToken: string) {
    const tokens = await this.refreshTokenRepo.find({
      where: {
        userId,
        isRevoked: false,
      },
    });

    for (const token of tokens) {
      const isMatch = await bcrypt.compare(refreshToken, token.tokenHash);

      if (isMatch && token.expiresAt > new Date()) {
        return token;
      }
    }

    return null;
  }

  async revokeRefreshToken(id: string) {
    await this.refreshTokenRepo.update(id, {
      isRevoked: true,
    });
  }

  async revokeAllUserTokens(userId: string) {
    await this.refreshTokenRepo.update(
      { userId, isRevoked: false },
      { isRevoked: true },
    );
  }
  async createPasswordResetToken(userId: string) {
  const plainToken = randomBytes(32).toString('hex');
  const tokenHash = await bcrypt.hash(plainToken, 10);

  const expiresAt = new Date();
  expiresAt.setMinutes(expiresAt.getMinutes() + 15);

  const resetToken = this.passwordResetRepo.create({
    userId,
    tokenHash,
    expiresAt,
  });

  await this.passwordResetRepo.save(resetToken);

  return plainToken;
}

async validatePasswordResetToken(userId: string, plainToken: string) {
  const tokens = await this.passwordResetRepo.find({
    where: {
      userId,
      isUsed: false,
    },
  });

  for (const token of tokens) {
    const isMatch = await bcrypt.compare(plainToken, token.tokenHash);

    if (isMatch && token.expiresAt > new Date()) {
      return token;
    }
  }

  return null;
}

async markPasswordResetTokenAsUsed(id: string) {
  await this.passwordResetRepo.update(id, {
    isUsed: true,
  });
}
}

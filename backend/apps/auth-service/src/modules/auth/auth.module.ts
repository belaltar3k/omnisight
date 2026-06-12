import { Module } from '@nestjs/common';
import { JwtModule } from '@nestjs/jwt';
import { PassportModule } from '@nestjs/passport'; // ← ADD THIS IMPORT
import { ConfigModule, ConfigService } from '@nestjs/config';
import { AuthService } from './auth.service';
import { AuthController } from './auth.controller';
import { UsersModule } from '../users/user.modules';
import { JwtStrategy } from '../../../../../libs/common/src/strategies/jwt.strategy';
import { TokensModule } from '../tokens/tokens.module';

@Module({
  imports: [
    UsersModule,
    TokensModule,
    PassportModule.register({ defaultStrategy: 'jwt' }), // ← ADD THIS LINE
    JwtModule.registerAsync({
      imports: [ConfigModule],
      inject: [ConfigService],
      useFactory: (config: ConfigService) => {
        const secret = config.get<string>('JWT_ACCESS_SECRET');
        if (!secret) throw new Error('JWT_ACCESS_SECRET is missing');
        return { secret, signOptions: { expiresIn: '15m' } };
      },
    }),
  ],
  controllers: [AuthController],
  providers: [AuthService, JwtStrategy],
})
export class AuthModule {}
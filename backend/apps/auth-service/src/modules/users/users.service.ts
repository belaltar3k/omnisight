import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { User } from './entities/auth.entity';
import { Repository } from 'typeorm';

@Injectable()
export class UsersService {
  constructor(
    @InjectRepository(User)
    private readonly userRepository: Repository<User>,
  ) {}

  async findByEmail(email: string) {
    return this.userRepository.findOne({
      where: { email },
    });
  }

  async findByEmployeeCode(employeeCode: string) {
    return this.userRepository.findOne({
      where: { employeeCode },
    });
  }

  // Generates a unique employee code (e.g. EMP-482917). Retries on the
  // off-chance of a random collision; the DB unique constraint is the backstop.
  async generateUniqueEmployeeCode(): Promise<string> {
    for (let attempt = 0; attempt < 10; attempt++) {
      const code = `EMP-${Math.floor(100000 + Math.random() * 900000)}`;
      const exists = await this.userRepository.findOne({
        where: { employeeCode: code },
      });
      if (!exists) {
        return code;
      }
    }
    throw new Error('Failed to generate a unique employee code');
  }

  async create(data: Partial<User>) {
    const user = this.userRepository.create(data);
    return this.userRepository.save(user);
  }

  async updatePassword(userId: string, passwordHash: string) {
  await this.userRepository.update(userId, {
    passwordHash,
  });
}
async findById(id: string) {
  return this.userRepository.findOne({
    where: { id },
  });
}

async delete(id: string) {
    return this.userRepository.delete(id);
  }
}

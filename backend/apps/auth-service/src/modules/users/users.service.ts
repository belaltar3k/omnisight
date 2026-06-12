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

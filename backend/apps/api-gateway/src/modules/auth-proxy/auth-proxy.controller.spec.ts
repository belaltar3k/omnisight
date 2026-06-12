import { Test, TestingModule } from '@nestjs/testing';
import { HttpService } from '@nestjs/axios';
import { AuthProxyController } from './auth-proxy.controller';

describe('AuthProxyController', () => {
  let controller: AuthProxyController;
  const httpService = {
    get: jest.fn(),
    post: jest.fn(),
  };

  beforeEach(async () => {
    const module: TestingModule = await Test.createTestingModule({
      controllers: [AuthProxyController],
      providers: [
        {
          provide: HttpService,
          useValue: httpService,
        },
      ],
    }).compile();

    controller = module.get<AuthProxyController>(AuthProxyController);
  });

  it('should be defined', () => {
    expect(controller).toBeDefined();
  });
});

import { IUser } from "./user.interface";
import { UserRole } from "@shared/enums";

export interface ICreateUserRequest {
  fullName: string;
  email: string;
  password: string;
  role: UserRole;
}

export interface ICreateUserResponse extends IUser {}

import { inject, Injectable } from "@angular/core";
import { userApiEndpoints } from "@environments";
import { Observable } from "rxjs";
import { HttpClient } from "@angular/common/http";
import {
  IUser,
  ICreateUserRequest,
  IUpdateUserRequest,
} from "@shared/interfaces/user";

@Injectable({
  providedIn: "root",
})
export class UserService {
  private readonly httpClient = inject(HttpClient);

  createUser(body: ICreateUserRequest): Observable<IUser> {
    return this.httpClient.post<IUser>(userApiEndpoints.createUser, body);
  }

  getUsers(): Observable<IUser[]> {
    return this.httpClient.get<IUser[]>(userApiEndpoints.getUsers);
  }

  getUserById(id: string): Observable<IUser> {
    return this.httpClient.get<IUser>(userApiEndpoints.getUserById(id));
  }

  updateUser(id: string, body: IUpdateUserRequest): Observable<IUser> {
    return this.httpClient.patch<IUser>(userApiEndpoints.updateUser(id), body);
  }

  deleteUser(id: string): Observable<void> {
    return this.httpClient.delete<void>(userApiEndpoints.deleteUser(id));
  }
}

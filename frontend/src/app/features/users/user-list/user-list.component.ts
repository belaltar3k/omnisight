import { AsyncPipe, SlicePipe } from "@angular/common";
import { Component, inject } from "@angular/core";
import { UserService } from "@core/services";
import { ModalService } from "@core/services/modal.service";
import { BtnStylesEnum, UserRole, UserStatus } from "@shared/enums";
import { ButtonComponent } from "@common/components/button/button.component";
import { IUser } from "@shared/interfaces/user";
import { ToastrService } from "ngx-toastr";

@Component({
  selector: "app-user-list",
  standalone: true,
  templateUrl: "./user-list.component.html",
  imports: [AsyncPipe, SlicePipe, ButtonComponent],
})
export class UserListComponent {
  private readonly userService = inject(UserService);
  private readonly modalService = inject(ModalService);
  private readonly toastr = inject(ToastrService);

  users$ = this.userService.getUsers();
  readonly UserStatus = UserStatus;
  protected readonly BtnStylesEnum = BtnStylesEnum;

  openCreateUserModal(): void {
    this.modalService.open({
      title: 'Create User',
      submitLabel: 'Create User',
      fields: [
        { key: 'fullName', label: 'Full Name', type: 'text', placeholder: 'Enter full name', required: true },
        { key: 'email', label: 'Email', type: 'email', placeholder: 'Enter email address', required: true },
        { key: 'password', label: 'Password', type: 'password', placeholder: 'Enter password', required: true },
        {
          key: 'role', label: 'Role', type: 'select', placeholder: 'Select a role', required: true,
          options: [
            { label: 'Admin', value: UserRole.Admin },
            { label: 'Supervisor', value: UserRole.Supervisor },
            { label: 'Security Guard', value: UserRole.SecurityGuard },
          ],
        },
      ],
      onSubmit: (data) => this.userService.createUser(data as never),
      onSuccess: () => { this.users$ = this.userService.getUsers(); },
    });
  }

  openEditUserModal(user: IUser): void {
    this.modalService.open({
      title: 'Edit User',
      submitLabel: 'Save Changes',
      fields: [
        { key: 'fullName', label: 'Full Name', type: 'text', placeholder: user.fullName, required: true },
        {
          key: 'role', label: 'Role', type: 'select', placeholder: 'Select a role', required: true,
          options: [
            { label: 'Admin', value: UserRole.Admin },
            { label: 'Supervisor', value: UserRole.Supervisor },
            { label: 'Security Guard', value: UserRole.SecurityGuard },
          ],
        },
        {
          key: 'status', label: 'Status', type: 'select', placeholder: 'Select status', required: true,
          options: [
            { label: 'Active', value: UserStatus.Active },
            { label: 'Inactive', value: UserStatus.Inactive },
            { label: 'Locked', value: UserStatus.Locked },
          ],
        },
      ],
      onSubmit: (data) => this.userService.updateUser(user.id, data as never),
      onSuccess: () => { this.users$ = this.userService.getUsers(); },
    });
  }

  deleteUser(user: IUser): void {
    if (!confirm(`Delete user "${user.fullName}"? This cannot be undone.`)) return;
    this.userService.deleteUser(user.id).subscribe({
      next: () => {
        this.toastr.success('User deleted');
        this.users$ = this.userService.getUsers();
      },
    });
  }
}
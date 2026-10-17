import * as people from "./people.ts";
import type {User} from "./people.ts";
import * as settings_data from "./settings_data.ts";
import {current_user, realm} from "./state_data.ts";

export function user_can_manage_user_activation(): boolean {
    return settings_data.user_has_permission_for_group_setting(
        realm.realm_miatsuco_can_manage_user_activation_group,
        "miatsuco_can_manage_user_activation_group",
        "realm",
    );
}

export function user_can_change_user_roles(): boolean {
    return settings_data.user_has_permission_for_group_setting(
        realm.realm_miatsuco_can_change_user_roles_group,
        "miatsuco_can_change_user_roles_group",
        "realm",
    );
}

export function user_can_edit_user_names(): boolean {
    return settings_data.user_has_permission_for_group_setting(
        realm.realm_miatsuco_can_edit_user_names_group,
        "miatsuco_can_edit_user_names_group",
        "realm",
    );
}

// Mirrors UserProfile.can_admin_user in zerver/models/users.py.
export function can_manage_user(user: User, user_has_permission: () => boolean): boolean {
    if (user_has_permission()) {
        return (
            current_user.is_owner ||
            people.is_my_user_id(user.user_id) ||
            people.get_by_user_id(current_user.user_id).role < user.role
        );
    }
    return false;
}

// Mirrors the role assignment check in update_user_backend in zerver/views/users.py.
export function can_assign_role(role_code: number): boolean {
    return current_user.is_owner || people.get_by_user_id(current_user.user_id).role < role_code;
}

export function can_manage_any(user: User): boolean {
    if (people.is_my_user_id(user.user_id)) {
        return current_user.is_admin;
    }
    return (
        current_user.is_admin ||
        can_manage_user(user, user_can_manage_user_activation) ||
        can_manage_user(user, user_can_change_user_roles) ||
        can_manage_user(user, user_can_edit_user_names)
    );
}

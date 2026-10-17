"use strict";

const assert = require("node:assert/strict");

const {make_realm} = require("./lib/example_realm.cjs");
const {make_user} = require("./lib/example_user.cjs");
const {zrequire} = require("./lib/namespace.cjs");
const {run_test} = require("./lib/test.cjs");

const people = zrequire("people");
const {set_current_user, set_realm} = zrequire("state_data");
const user_management = zrequire("miatsuco_user_management");

const OWNER = 100;
const ADMIN = 200;
const MODERATOR = 300;
const MEMBER = 400;
const GUEST = 600;

const realm = make_realm({});
set_realm(realm);

const me = make_user({email: "me@example.com", user_id: 1, full_name: "Me"});
const owner = make_user({email: "owner@example.com", user_id: 2, full_name: "Owner"});
const admin = make_user({email: "admin@example.com", user_id: 3, full_name: "Admin"});
const moderator = make_user({email: "mod@example.com", user_id: 4, full_name: "Moderator"});
const member = make_user({email: "member@example.com", user_id: 5, full_name: "Member"});
const guest = make_user({email: "guest@example.com", user_id: 6, full_name: "Guest"});

owner.role = OWNER;
admin.role = ADMIN;
moderator.role = MODERATOR;
member.role = MEMBER;
guest.role = GUEST;

people.init();
for (const user of [me, owner, admin, moderator, member, guest]) {
    people.add_active_user(user);
}
people.initialize_current_user(me.user_id);

function become(role) {
    set_current_user({
        user_id: me.user_id,
        is_owner: role === OWNER,
        is_admin: role === OWNER || role === ADMIN,
        is_moderator: role === OWNER || role === ADMIN || role === MODERATOR,
        is_guest: role === GUEST,
    });
    me.role = role;
}

function set_groups(user_ids) {
    const group = {direct_members: user_ids, direct_subgroups: []};
    realm.realm_miatsuco_can_manage_user_activation_group = group;
    realm.realm_miatsuco_can_change_user_roles_group = group;
    realm.realm_miatsuco_can_edit_user_names_group = group;
}

run_test("users outside the group cannot manage anyone", () => {
    set_groups([]);
    become(MODERATOR);

    for (const has_permission of [
        user_management.user_can_manage_user_activation,
        user_management.user_can_change_user_roles,
        user_management.user_can_edit_user_names,
    ]) {
        assert.ok(!user_management.can_manage_user(member, has_permission));
    }
    assert.ok(!user_management.can_manage_any(member));
});

run_test("group members act only on lower roles", () => {
    set_groups([me.user_id]);
    become(MODERATOR);

    assert.ok(
        user_management.can_manage_user(member, user_management.user_can_manage_user_activation),
    );
    assert.ok(user_management.can_manage_user(guest, user_management.user_can_edit_user_names));
    assert.ok(
        !user_management.can_manage_user(moderator, user_management.user_can_change_user_roles),
    );
    assert.ok(!user_management.can_manage_user(admin, user_management.user_can_edit_user_names));
    assert.ok(
        !user_management.can_manage_user(owner, user_management.user_can_manage_user_activation),
    );
    assert.ok(user_management.can_manage_any(member));

    become(ADMIN);
    assert.ok(
        user_management.can_manage_user(moderator, user_management.user_can_change_user_roles),
    );
    assert.ok(!user_management.can_manage_user(admin, user_management.user_can_change_user_roles));
    assert.ok(!user_management.can_manage_user(owner, user_management.user_can_change_user_roles));
});

run_test("owners can act on everyone in the group", () => {
    set_groups([me.user_id]);
    become(OWNER);

    for (const user of [owner, admin, moderator, member, guest]) {
        assert.ok(
            user_management.can_manage_user(user, user_management.user_can_manage_user_activation),
        );
    }

    set_groups([]);
    assert.ok(
        !user_management.can_manage_user(member, user_management.user_can_manage_user_activation),
    );
});

run_test("administrators can always edit other profile fields", () => {
    set_groups([]);
    become(ADMIN);
    assert.ok(user_management.can_manage_any(member));
});

run_test("only administrators can edit their own profile fields", () => {
    set_groups([me.user_id]);

    become(MODERATOR);
    assert.ok(!user_management.can_manage_any(me));

    become(ADMIN);
    assert.ok(user_management.can_manage_any(me));
});

run_test("assignable roles", () => {
    become(MODERATOR);
    assert.ok(!user_management.can_assign_role(MODERATOR));
    assert.ok(user_management.can_assign_role(MEMBER));
    assert.ok(user_management.can_assign_role(GUEST));

    become(ADMIN);
    assert.ok(!user_management.can_assign_role(ADMIN));
    assert.ok(user_management.can_assign_role(MODERATOR));

    become(OWNER);
    assert.ok(user_management.can_assign_role(OWNER));
});

run_test("each permission follows its own group", () => {
    const settings = [
        [
            "realm_miatsuco_can_manage_user_activation_group",
            user_management.user_can_manage_user_activation,
        ],
        ["realm_miatsuco_can_change_user_roles_group", user_management.user_can_change_user_roles],
        ["realm_miatsuco_can_edit_user_names_group", user_management.user_can_edit_user_names],
    ];
    become(MODERATOR);

    for (const [setting_name] of settings) {
        set_groups([]);
        realm[setting_name] = {direct_members: [me.user_id], direct_subgroups: []};
        for (const [other_setting_name, has_permission] of settings) {
            assert.equal(
                user_management.can_manage_user(member, has_permission),
                other_setting_name === setting_name,
            );
        }
    }
});

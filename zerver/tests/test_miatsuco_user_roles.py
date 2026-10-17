from zerver.lib.test_miatsuco import MiatsucoUserManagementTestMixin
from zerver.models import UserProfile
from zerver.models.groups import SystemGroups

ROLES = "miatsuco_can_change_user_roles_group"


class MiatsucoUserRolesTest(MiatsucoUserManagementTestMixin):
    def test_roles(self) -> None:
        hamlet, othello, iago, shiva, desdemona = (
            self.example_user(name) for name in ["hamlet", "othello", "iago", "shiva", "desdemona"]
        )

        self.login_user(iago)
        self.assert_json_success(self.api_set_user_role(hamlet, UserProfile.ROLE_MODERATOR))
        self.assert_json_error(
            self.api_set_user_role(hamlet, UserProfile.ROLE_REALM_ADMINISTRATOR),
            self.DENIED_ERROR,
        )
        self.assert_json_success(self.api_set_user_role(shiva, UserProfile.ROLE_MEMBER))

        self.set_user_role(othello, UserProfile.ROLE_REALM_ADMINISTRATOR)
        self.assert_json_error(
            self.api_set_user_role(othello, UserProfile.ROLE_MEMBER), self.DENIED_ERROR
        )
        self.assert_json_error(
            self.api_set_user_role(desdemona, UserProfile.ROLE_MEMBER), self.OWNER_ONLY_ERROR
        )
        self.assert_json_success(self.api_set_user_role(iago, UserProfile.ROLE_MEMBER))

        self.login_user(desdemona)
        self.assert_json_success(self.api_set_user_role(othello, UserProfile.ROLE_MEMBER))
        self.assert_json_success(self.api_set_user_role(othello, UserProfile.ROLE_REALM_OWNER))

    def test_roles_with_moderators_in_group(self) -> None:
        cordelia, hamlet, shiva = (
            self.example_user(name) for name in ["cordelia", "hamlet", "shiva"]
        )
        self.set_realm_group_setting(ROLES, SystemGroups.MODERATORS)

        self.login_user(shiva)
        self.assert_json_success(self.api_set_user_role(hamlet, UserProfile.ROLE_GUEST))
        self.assert_json_error(
            self.api_set_user_role(hamlet, UserProfile.ROLE_MODERATOR), self.DENIED_ERROR
        )
        self.assert_json_error(
            self.api_set_user_role(cordelia, UserProfile.ROLE_REALM_ADMINISTRATOR),
            self.DENIED_ERROR,
        )

        self.login_user(cordelia)
        self.assert_json_error(
            self.api_set_user_role(hamlet, UserProfile.ROLE_MEMBER), self.DENIED_ERROR
        )

    def test_bot_role_is_unchanged(self) -> None:
        shiva = self.example_user("shiva")
        self.set_user_role(shiva, UserProfile.ROLE_MODERATOR)
        self.set_realm_group_setting(ROLES, SystemGroups.MODERATORS)
        bot = self.create_bot()

        self.login_user(shiva)
        result = self.api_set_user_role(bot, UserProfile.ROLE_GUEST)
        self.assert_json_error(result, "Must be an organization administrator")

        self.login("iago")
        self.assert_json_success(self.api_set_user_role(bot, UserProfile.ROLE_GUEST))

    def test_user_in_another_realm_is_unchanged(self) -> None:
        self.assertFalse(self.example_user("desdemona").can_admin_user(self.mit_user("sipbtest")))

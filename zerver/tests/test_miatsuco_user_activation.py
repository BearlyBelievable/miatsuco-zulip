from zerver.actions.realm_settings import do_change_realm_permission_group_setting
from zerver.actions.user_groups import check_add_user_group
from zerver.lib.test_miatsuco import MiatsucoUserManagementTestMixin
from zerver.models import UserProfile
from zerver.models.groups import SystemGroups
from zerver.models.realms import get_realm

ACTIVATION = "miatsuco_can_manage_user_activation_group"


class MiatsucoUserActivationTest(MiatsucoUserManagementTestMixin):
    def test_activation(self) -> None:
        hamlet, iago, shiva, desdemona, cordelia, othello = (
            self.example_user(name)
            for name in ["hamlet", "iago", "shiva", "desdemona", "cordelia", "othello"]
        )

        self.login_user(shiva)
        self.assert_json_error(self.api_deactivate_user(hamlet), self.DENIED_ERROR)

        self.login_user(iago)
        self.assert_json_success(self.api_deactivate_user(hamlet))
        self.assert_json_success(self.api_reactivate_user(hamlet))
        self.set_user_role(othello, UserProfile.ROLE_REALM_ADMINISTRATOR)
        self.assert_json_error(self.api_deactivate_user(othello), self.DENIED_ERROR)
        self.assert_json_error(self.api_deactivate_user(desdemona), self.OWNER_ONLY_ERROR)

        self.set_realm_group_setting(ACTIVATION, SystemGroups.MODERATORS)
        self.login_user(shiva)
        self.assert_json_success(self.api_deactivate_user(hamlet))
        self.assert_json_success(self.api_reactivate_user(hamlet))
        self.assert_json_error(self.api_deactivate_user(iago), self.DENIED_ERROR)

        self.login_user(desdemona)
        self.assert_json_success(self.api_deactivate_user(iago))
        self.assert_json_success(self.api_reactivate_user(iago))

        self.set_realm_group_setting(ACTIVATION, SystemGroups.NOBODY)
        self.assert_json_error(self.api_deactivate_user(cordelia), self.DENIED_ERROR)

    def test_activation_with_custom_group(self) -> None:
        realm = get_realm("zulip")
        cordelia = self.example_user("cordelia")
        hamlet = self.example_user("hamlet")
        group = check_add_user_group(
            realm, "deactivators", [cordelia], acting_user=self.example_user("desdemona")
        )
        do_change_realm_permission_group_setting(realm, ACTIVATION, group, acting_user=None)

        self.login_user(cordelia)
        self.assert_json_error(self.api_deactivate_user(hamlet), self.DENIED_ERROR)
        self.set_user_role(cordelia, UserProfile.ROLE_MODERATOR)
        self.assert_json_success(self.api_deactivate_user(hamlet))

        self.login_user(self.example_user("othello"))
        self.assert_json_error(self.api_reactivate_user(hamlet), self.DENIED_ERROR)

    def test_bot_activation_is_unchanged(self) -> None:
        shiva = self.example_user("shiva")
        self.set_user_role(shiva, UserProfile.ROLE_MODERATOR)
        self.set_realm_group_setting(ACTIVATION, SystemGroups.MODERATORS)
        bot = self.create_bot()

        self.login_user(shiva)
        self.assert_json_error(self.client_delete(f"/json/bots/{bot.id}"), self.DENIED_ERROR)

        self.login("iago")
        self.assert_json_success(self.client_delete(f"/json/bots/{bot.id}"))

        self.login_user(shiva)
        self.assert_json_error(self.api_reactivate_user(bot), self.DENIED_ERROR)

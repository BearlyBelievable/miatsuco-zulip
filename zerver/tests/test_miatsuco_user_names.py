import orjson

from zerver.lib.test_miatsuco import MiatsucoUserManagementTestMixin
from zerver.models import UserProfile
from zerver.models.groups import SystemGroups

NAMES = "miatsuco_can_edit_user_names_group"


class MiatsucoUserNamesTest(MiatsucoUserManagementTestMixin):
    def test_names(self) -> None:
        hamlet, iago, shiva, desdemona = (
            self.example_user(name) for name in ["hamlet", "iago", "shiva", "desdemona"]
        )

        self.login_user(shiva)
        self.assert_json_error(self.api_patch_user(hamlet, full_name="Renamed"), self.DENIED_ERROR)

        self.set_realm_group_setting(NAMES, SystemGroups.MODERATORS)
        self.assert_json_success(self.api_patch_user(hamlet, full_name="Renamed"))
        hamlet.refresh_from_db()
        self.assertEqual(hamlet.full_name, "Renamed")
        self.assert_json_error(
            self.api_patch_user(iago, full_name="Renamed again"), self.DENIED_ERROR
        )
        profile_data = orjson.dumps([{"id": 1, "value": "x"}]).decode()
        self.assert_json_error(
            self.api_patch_user(hamlet, profile_data=profile_data), self.DENIED_ERROR
        )

        self.login_user(iago)
        self.assert_json_success(self.api_patch_user(hamlet, full_name="Renamed twice"))
        self.assert_json_error(
            self.api_patch_user(desdemona, full_name="Renamed owner"), self.DENIED_ERROR
        )

        self.login_user(desdemona)
        self.assert_json_success(self.api_patch_user(iago, full_name="Renamed admin"))

    def test_bot_name_is_unchanged(self) -> None:
        shiva = self.example_user("shiva")
        self.set_user_role(shiva, UserProfile.ROLE_MODERATOR)
        self.set_realm_group_setting(NAMES, SystemGroups.MODERATORS)
        bot = self.create_bot()

        self.login_user(shiva)
        self.assert_json_error(self.api_patch_user(bot, full_name="Renamed bot"), self.DENIED_ERROR)

        self.login("iago")
        self.assert_json_success(self.api_patch_user(bot, full_name="Renamed bot"))

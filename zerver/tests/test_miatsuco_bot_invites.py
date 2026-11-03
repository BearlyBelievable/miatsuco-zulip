from typing import TYPE_CHECKING

import orjson

from zerver.actions.realm_settings import (
    do_change_realm_permission_group_setting,
    do_set_realm_property,
)
from zerver.actions.users import do_change_user_role
from zerver.lib.test_classes import ZulipTestCase
from zerver.models import NamedUserGroup, PreregistrationUser, UserProfile
from zerver.models.groups import SystemGroups

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse as TestHttpResponse

BOT_REFUSAL = "This endpoint does not accept bot requests."
BOT_OWNER_ERROR = "Only bots owned by an administrator can send invitations."
INVITEE = "alice-test@zulip.com"


class MiatsucoBotInvitesTest(ZulipTestCase):
    def send_invite(
        self, bot: UserProfile, invite_as: int = PreregistrationUser.INVITE_AS["MEMBER"]
    ) -> "TestHttpResponse":
        return self.api_post(
            bot,
            "/api/v1/invites",
            {
                "invitee_emails": INVITEE,
                "stream_ids": orjson.dumps([self.get_stream_id("Denmark")]).decode(),
                "invite_as": invite_as,
            },
        )

    def test_bot_invitations(self) -> None:
        iago = self.example_user("iago")
        realm = iago.realm
        admin_owned_bot = self.create_test_bot("adminowned", iago, "Admin owned bot")
        member_owned_bot = self.create_test_bot(
            "memberowned", self.example_user("hamlet"), "Member owned bot"
        )

        self.assert_json_error(self.send_invite(admin_owned_bot), BOT_REFUSAL)

        do_set_realm_property(realm, "miatsuco_bots_can_invite_users", True, acting_user=None)
        self.assert_json_error(self.send_invite(member_owned_bot), BOT_OWNER_ERROR)

        self.assert_json_error(
            self.send_invite(admin_owned_bot, PreregistrationUser.INVITE_AS["REALM_ADMIN"]),
            "Must be an organization administrator",
        )

        self.assert_json_success(self.send_invite(admin_owned_bot))
        prereg_user = PreregistrationUser.objects.get(email=INVITEE)
        self.assertEqual(prereg_user.referred_by, admin_owned_bot)

        multiuse_result = self.api_post(
            admin_owned_bot,
            "/api/v1/invites/multiuse",
            {"stream_ids": orjson.dumps([self.get_stream_id("Denmark")]).decode()},
            intentionally_undocumented=True,
        )
        self.assert_json_error(multiuse_result, BOT_REFUSAL)

        nobody_group = NamedUserGroup.objects.get(
            name=SystemGroups.NOBODY, realm_for_sharding=realm, is_system_group=True
        )
        do_change_realm_permission_group_setting(
            realm, "can_invite_users_group", nobody_group, acting_user=None
        )
        self.assert_json_error(self.send_invite(admin_owned_bot), "Insufficient permission")

        do_change_realm_permission_group_setting(
            realm,
            "can_invite_users_group",
            NamedUserGroup.objects.get(
                name=SystemGroups.MEMBERS, realm_for_sharding=realm, is_system_group=True
            ),
            acting_user=None,
        )
        do_change_user_role(admin_owned_bot, UserProfile.ROLE_GUEST, acting_user=None, notify=False)
        self.assert_json_error(self.send_invite(admin_owned_bot), "Not allowed for guest users")

        do_change_user_role(iago, UserProfile.ROLE_MEMBER, acting_user=None, notify=False)
        do_change_user_role(
            admin_owned_bot, UserProfile.ROLE_MEMBER, acting_user=None, notify=False
        )
        self.assert_json_error(self.send_invite(admin_owned_bot), BOT_OWNER_ERROR)

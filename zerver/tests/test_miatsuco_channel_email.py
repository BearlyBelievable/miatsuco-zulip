from email.message import EmailMessage
from typing import TYPE_CHECKING

from typing_extensions import override

from zerver.actions.users import do_deactivate_user
from zerver.lib.email_mirror import process_message
from zerver.lib.email_mirror_helpers import encode_email_address
from zerver.lib.test_classes import ZulipTestCase
from zerver.models import ChannelEmailAddress, UserProfile
from zerver.models.realms import get_realm
from zerver.models.streams import get_stream
from zerver.models.users import get_system_bot

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse as TestHttpResponse

LOGGER_NAME = "zerver.lib.email_mirror"


class MiatsucoChannelEmailTest(ZulipTestCase):
    @override
    def setUp(self) -> None:
        super().setUp()
        self.realm = get_realm("zulip")
        self.channel = get_stream("Denmark", self.realm)
        self.url = f"/json/streams/{self.channel.id}"
        self.iago = self.example_user("iago")
        self.hamlet = self.example_user("hamlet")
        self.cordelia = self.example_user("cordelia")
        self.gateway_bot = get_system_bot("emailgateway@zulip.com", self.realm.id)

    def create_row(self, creator: UserProfile, sender: UserProfile) -> ChannelEmailAddress:
        return ChannelEmailAddress.objects.create(
            realm=self.realm, channel=self.channel, creator=creator, sender=sender
        )

    def encoded(self, row: ChannelEmailAddress) -> str:
        return encode_email_address(self.channel.name, row.email_token, show_sender=True)

    def revoke(self, user: UserProfile, row: ChannelEmailAddress) -> "TestHttpResponse":
        self.login_user(user)
        return self.client_delete(f"{self.url}/email_addresses/{row.id}")

    def list_addresses(self, user: UserProfile) -> list[dict[str, object]]:
        self.login_user(user)
        result = self.client_get(f"{self.url}/email_addresses")
        return self.assert_json_success(result)["email_addresses"]

    def assert_revoked(self, address: str) -> None:
        email_message = EmailMessage()
        email_message.set_content("message body")
        email_message["Subject"] = "test subject"
        email_message["From"] = "sender@example.com"
        email_message["To"] = address
        with self.assertLogs(LOGGER_NAME, level="INFO") as logs:
            process_message(email_message)
        self.assertTrue(any("Bad stream token" in line for line in logs.output))

    def test_listing_addresses(self) -> None:
        own = self.create_row(self.hamlet, self.hamlet)
        gateway = self.create_row(self.hamlet, self.gateway_bot)
        other = self.create_row(self.cordelia, self.cordelia)

        member_view = self.list_addresses(self.hamlet)
        self.assertEqual([row["id"] for row in member_view], [own.id, gateway.id])
        self.assertEqual(member_view[0]["email"], self.encoded(own))
        self.assertEqual(member_view[0]["sender_id"], self.hamlet.id)
        self.assertEqual(member_view[1]["sender_id"], self.gateway_bot.id)
        self.assertEqual(self.list_addresses(self.cordelia)[0]["id"], other.id)

        admin_view = self.list_addresses(self.iago)
        self.assertEqual([row["id"] for row in admin_view], [own.id, gateway.id, other.id])
        self.assertEqual([row["email"] for row in admin_view], [None, None, None])
        iago_row = self.create_row(self.iago, self.iago)
        self.assertEqual(self.list_addresses(self.iago)[-1]["email"], self.encoded(iago_row))

    def test_revoking_addresses(self) -> None:
        own = self.create_row(self.hamlet, self.hamlet)
        other = self.create_row(self.cordelia, self.cordelia)

        self.assert_json_error(self.revoke(self.hamlet, other), "No such channel email address.")
        self.assert_json_success(self.revoke(self.hamlet, own))
        self.assert_revoked(self.encoded(own))
        self.assert_json_error(self.revoke(self.hamlet, own), "No such channel email address.")

        self.assert_json_success(self.revoke(self.iago, other))
        self.assert_revoked(self.encoded(other))

    def test_deactivating_a_user_revokes_their_addresses(self) -> None:
        created = self.create_row(self.hamlet, self.gateway_bot)
        sent_as = self.create_row(self.cordelia, self.hamlet)
        unrelated = self.create_row(self.cordelia, self.cordelia)

        do_deactivate_user(self.hamlet, acting_user=None)
        self.assertFalse(ChannelEmailAddress.objects.filter(id=created.id).exists())
        self.assertFalse(ChannelEmailAddress.objects.filter(id=sent_as.id).exists())
        self.assertTrue(ChannelEmailAddress.objects.filter(id=unrelated.id).exists())

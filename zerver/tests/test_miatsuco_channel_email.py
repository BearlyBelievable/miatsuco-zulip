from importlib import import_module

import orjson
from django.apps import apps

from zerver.actions.streams import do_set_stream_property
from zerver.actions.users import do_deactivate_user
from zerver.lib.email_mirror import validate_to_address
from zerver.lib.email_mirror_helpers import ZulipEmailForwardError
from zerver.lib.miatsuco_channel_email import is_personal_channel_email_address
from zerver.lib.test_miatsuco import MiatsucoChannelEmailAddressTestMixin
from zerver.models import ChannelEmailAddress
from zerver.models.streams import get_stream


class MiatsucoChannelEmailTest(MiatsucoChannelEmailAddressTestMixin):
    def test_setting(self) -> None:
        self.login_user(self.hamlet)
        stream = self.assert_json_success(self.client_get(self.url))["stream"]
        self.assertFalse(stream["miatsuco_allow_user_email_posting"])
        self.assert_json_error(
            self.generate(self.hamlet, sender_id=self.hamlet.id),
            "Messaging this channel by email is not enabled.",
        )

        data = {"miatsuco_allow_user_email_posting": orjson.dumps(True).decode()}
        self.login_user(self.hamlet)
        result = self.client_patch(self.url, data)
        self.assert_json_error(result, "You do not have permission to administer this channel.")

        self.login_user(self.iago)
        with self.capture_send_event_calls(expected_num_events=1) as events:
            result = self.client_patch(self.url, data)
        self.assert_json_success(result)
        self.assertEqual(events[0]["event"]["property"], "miatsuco_allow_user_email_posting")
        self.assertTrue(get_stream("Denmark", self.realm).miatsuco_allow_user_email_posting)

    def test_generating_a_personal_address(self) -> None:
        self.enable()
        own = {"sender_id": self.hamlet.id}
        address = self.assert_json_success(self.generate(self.hamlet, **own))["email"]
        self.assertNotIn(".show-sender", address)
        self.assertEqual(
            self.assert_json_success(self.generate(self.hamlet, **own))["email"], address
        )
        self.assertEqual([item["email"] for item in self.list_addresses(self.hamlet)], [address])

        self.assertEqual(self.deliver(address), self.delivery_log(None))
        self.assertEqual(self.get_last_message().sender_id, self.hamlet.id)

        self.assert_json_success(self.generate(self.hamlet))

    def test_channels_with_personal_addresses_allow_them(self) -> None:
        bot = self.create_test_bot("self_bot", self.hamlet, full_name="Self bot")
        self.create_row(self.hamlet, self.hamlet)
        self.create_row(self.cordelia, self.gateway_bot, "Verona")
        ChannelEmailAddress.objects.create(
            realm=self.realm, channel=get_stream("Scotland", self.realm), creator=bot, sender=bot
        )

        migration = import_module(
            "zerver.migrations.miatsuco_0019_stream_user_email_posting_backfill"
        )
        migration.enable_personal_addresses_for_channels_using_them(apps, None)

        self.assertTrue(get_stream("Denmark", self.realm).miatsuco_allow_user_email_posting)
        self.assertFalse(get_stream("Verona", self.realm).miatsuco_allow_user_email_posting)
        self.assertFalse(get_stream("Scotland", self.realm).miatsuco_allow_user_email_posting)

    def test_a_bot_acting_as_itself_is_not_personal(self) -> None:
        bot = self.create_test_bot("self_bot", self.hamlet, full_name="Self bot")
        result = self.api_get(
            bot, f"/api/v1/streams/{self.channel.id}/email_address", {"sender_id": bot.id}
        )
        self.assert_json_success(result)
        row = ChannelEmailAddress.objects.get(creator=bot, sender=bot)
        self.assertFalse(is_personal_channel_email_address(row))
        self.assertEqual(self.deliver(self.encoded(row)), self.delivery_log(None))

    def test_listing_addresses(self) -> None:
        own = self.create_row(self.hamlet, self.hamlet)
        gateway = self.create_row(self.hamlet, self.gateway_bot)
        other = self.create_row(self.cordelia, self.cordelia)
        self.create_row(self.hamlet, self.hamlet, "Verona")

        member_view = {item["id"]: item for item in self.list_addresses(self.hamlet)}
        self.assertEqual(set(member_view), {own.id, gateway.id})
        self.assertTrue(member_view[own.id]["is_personal"])
        self.assertFalse(member_view[gateway.id]["is_personal"])
        self.assertEqual(member_view[own.id]["email"], self.encoded(own))
        self.assertEqual(member_view[gateway.id]["email"], self.encoded(gateway, show_sender=True))
        self.assertEqual([item["id"] for item in self.list_addresses(self.cordelia)], [other.id])

        admin_view = self.list_addresses(self.iago)
        self.assertEqual([item["id"] for item in admin_view], [own.id, gateway.id, other.id])
        self.assertEqual([item["email"] for item in admin_view], [None, None, None])
        iago_row = self.create_row(self.iago, self.iago)
        self.assertEqual(self.list_addresses(self.iago)[-1]["email"], self.encoded(iago_row))

    def test_revoking_addresses(self) -> None:
        own = self.create_row(self.hamlet, self.hamlet)
        other = self.create_row(self.cordelia, self.cordelia)
        other_channel = self.create_row(self.hamlet, self.hamlet, "Verona")

        self.assert_json_error(self.revoke(self.hamlet, other), "No such channel email address.")
        self.assert_json_error(
            self.revoke(self.hamlet, other_channel), "No such channel email address."
        )

        encoded = self.encoded(own)
        self.enable()
        self.assertEqual(self.deliver(encoded), self.delivery_log(None))
        self.assert_json_success(self.revoke(self.hamlet, own))
        with self.assertRaises(ZulipEmailForwardError):
            validate_to_address(encoded, rate_limit=False)
        self.assert_json_error(self.revoke(self.hamlet, own), "No such channel email address.")

        self.assert_json_success(self.revoke(self.iago, other))
        self.assertFalse(ChannelEmailAddress.objects.filter(id=other.id).exists())

        new_address = self.assert_json_success(
            self.generate(self.hamlet, sender_id=self.hamlet.id)
        )["email"]
        self.assertNotEqual(new_address.split(".")[1], own.email_token)

    def test_deactivating_a_user_revokes_their_addresses(self) -> None:
        created = self.create_row(self.hamlet, self.gateway_bot)
        sent_as = self.create_row(self.cordelia, self.hamlet)
        unrelated = self.create_row(self.cordelia, self.cordelia)

        do_deactivate_user(self.hamlet, acting_user=None)
        self.assertFalse(ChannelEmailAddress.objects.filter(id=created.id).exists())
        self.assertFalse(ChannelEmailAddress.objects.filter(id=sent_as.id).exists())
        self.assertTrue(ChannelEmailAddress.objects.filter(id=unrelated.id).exists())

    def test_turning_off_the_setting_revokes_personal_addresses(self) -> None:
        self.enable()
        personal = self.create_row(self.hamlet, self.hamlet)
        gateway = self.create_row(self.hamlet, self.gateway_bot)

        do_set_stream_property(self.channel, "miatsuco_allow_user_email_posting", False, self.iago)
        self.assertFalse(ChannelEmailAddress.objects.filter(id=personal.id).exists())
        self.assertTrue(ChannelEmailAddress.objects.filter(id=gateway.id).exists())

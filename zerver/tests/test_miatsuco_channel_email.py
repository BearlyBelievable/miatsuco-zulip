from importlib import import_module

import orjson
from django.apps import apps

from zerver.lib.email_mirror import validate_to_address
from zerver.lib.email_mirror_helpers import ZulipEmailForwardError
from zerver.lib.test_miatsuco import MiatsucoChannelEmailAddressTestMixin
from zerver.models import ChannelEmailAddress, UserProfile
from zerver.models.streams import get_stream


class MiatsucoChannelEmailTest(MiatsucoChannelEmailAddressTestMixin):
    def test_settings(self) -> None:
        self.login_user(self.hamlet)
        stream = self.assert_json_success(self.client_get(self.url))["stream"]
        self.assertFalse(stream["miatsuco_allow_email_posting"])
        self.assertFalse(stream["miatsuco_allow_user_email_posting"])
        self.assert_json_error(
            self.generate(self.hamlet, sender_id=self.hamlet.id),
            "Messaging this channel by email is not enabled.",
        )
        self.assert_json_error(
            self.generate(self.iago), "Posting by email is not enabled for this channel."
        )

        data = {
            "miatsuco_allow_email_posting": orjson.dumps(True).decode(),
            "miatsuco_allow_user_email_posting": orjson.dumps(True).decode(),
        }
        self.login_user(self.hamlet)
        result = self.client_patch(self.url, data)
        self.assert_json_error(result, "You do not have permission to administer this channel.")

        self.login_user(self.iago)
        with self.capture_send_event_calls(expected_num_events=2) as events:
            result = self.client_patch(self.url, data)
        self.assert_json_success(result)
        self.assertEqual({event["event"]["property"] for event in events}, set(data))
        channel = get_stream("Denmark", self.realm)
        self.assertTrue(channel.miatsuco_allow_email_posting)
        self.assertTrue(channel.miatsuco_allow_user_email_posting)

    def test_generating_addresses(self) -> None:
        self.enable(bot=False)
        own = {"sender_id": self.hamlet.id}
        address = self.assert_json_success(self.generate(self.hamlet, **own))["email"]
        self.assertNotIn(".show-sender", address)
        self.assertEqual(
            self.assert_json_success(self.generate(self.hamlet, **own))["email"], address
        )
        self.assertEqual([item["email"] for item in self.list_addresses(self.hamlet)], [address])
        self.assertEqual(self.deliver(address), self.delivery_log(None))

        self.enable()
        self.assert_json_error(
            self.generate(self.hamlet),
            "Only channel administrators can use a channel email address.",
        )
        self.make_channel_administrator(self.hamlet)
        self.assert_json_success(self.generate(self.hamlet))

        self.set_user_role(self.cordelia, UserProfile.ROLE_REALM_ADMINISTRATOR)
        iago_address = self.assert_json_success(self.generate(self.iago))["email"]
        self.assertEqual(self.assert_json_success(self.generate(self.iago))["email"], iago_address)
        self.assertNotEqual(
            self.assert_json_success(self.generate(self.cordelia))["email"], iago_address
        )

    def test_channels_using_the_email_gateway_allow_bot_addresses(self) -> None:
        self.send_stream_message(
            self.gateway_bot, "Denmark", "from a mailing list", recipient_realm=self.realm
        )
        migration = import_module("zerver.migrations.miatsuco_0021_stream_email_posting_backfill")
        migration.enable_bot_addresses_for_channels_using_the_email_gateway(apps, None)

        self.assertTrue(get_stream("Denmark", self.realm).miatsuco_allow_email_posting)
        self.assertFalse(get_stream("Verona", self.realm).miatsuco_allow_email_posting)

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

    def test_legacy_bot_addresses_are_detached_from_their_creators(self) -> None:
        legacy = self.create_row(self.hamlet, self.gateway_bot)
        ChannelEmailAddress.objects.filter(id=legacy.id).update(
            date_created=self.channel.date_created
        )
        recent = self.create_row(self.hamlet, self.gateway_bot, "Verona")
        personal = self.create_row(self.cordelia, self.cordelia)

        migration = import_module("zerver.migrations.miatsuco_0021_stream_email_posting_backfill")
        migration.detach_legacy_bot_addresses_from_creators(apps, None)

        for row, creator_id in [
            (legacy, None),
            (recent, self.hamlet.id),
            (personal, self.cordelia.id),
        ]:
            row.refresh_from_db()
            self.assertEqual(row.creator_id, creator_id)

    def test_a_bot_acting_as_itself_gets_a_bot_address(self) -> None:
        self.enable()
        error = "Only channel administrators can use a channel email address."
        bot = self.create_test_bot("self_bot", self.hamlet, full_name="Self bot")
        result = self.api_get(
            bot, f"/api/v1/streams/{self.channel.id}/email_address", {"sender_id": bot.id}
        )
        self.assert_json_error(result, error)

        row = self.create_row(bot, bot)
        self.assertEqual(self.deliver(self.encoded(row)), self.delivery_log(error))

    def test_listing_addresses(self) -> None:
        self.make_channel_administrator(self.hamlet)
        iago_personal = self.create_row(self.iago, self.iago)
        hamlet_personal = self.create_row(self.hamlet, self.hamlet)
        cordelia_personal = self.create_row(self.cordelia, self.cordelia)
        iago_bot = self.create_row(self.iago, self.gateway_bot)
        hamlet_bot = self.create_row(self.hamlet, self.gateway_bot)
        self.create_row(self.iago, self.gateway_bot, "Verona")

        iago_view = {item["id"]: item for item in self.list_addresses(self.iago)}
        self.assertEqual(
            set(iago_view),
            {
                iago_personal.id,
                hamlet_personal.id,
                cordelia_personal.id,
                iago_bot.id,
                hamlet_bot.id,
            },
        )
        self.assertEqual(iago_view[iago_bot.id]["creator_id"], self.iago.id)
        self.assertEqual(iago_view[iago_bot.id]["sender_id"], self.gateway_bot.id)
        self.assertEqual(iago_view[iago_bot.id]["email"], self.encoded(iago_bot, show_sender=True))
        self.assertEqual(
            iago_view[hamlet_bot.id]["email"], self.encoded(hamlet_bot, show_sender=True)
        )
        self.assertTrue(iago_view[iago_personal.id]["is_personal"])
        self.assertFalse(iago_view[iago_bot.id]["is_personal"])
        self.assertIsNotNone(iago_view[iago_personal.id]["email"])
        self.assertIsNone(iago_view[hamlet_personal.id]["email"])
        self.assertIsNone(iago_view[cordelia_personal.id]["email"])

        self.assertEqual(
            {item["id"] for item in self.list_addresses(self.hamlet)},
            {hamlet_personal.id, hamlet_bot.id},
        )
        self.assertEqual(
            [item["id"] for item in self.list_addresses(self.cordelia)], [cordelia_personal.id]
        )

    def test_revoking_addresses(self) -> None:
        unmanaged = self.create_row(self.hamlet, self.gateway_bot)
        self.assert_json_success(self.revoke(self.iago, unmanaged))

        self.enable()
        self.make_channel_administrator(self.cordelia)
        bot = self.create_row(self.iago, self.gateway_bot)
        personal = self.create_row(self.hamlet, self.hamlet)
        other_channel = self.create_row(self.iago, self.gateway_bot, "Verona")
        encoded = self.encoded(bot)
        self.assertEqual(self.deliver(encoded), self.delivery_log(None))

        for user, row in [
            (self.hamlet, bot),
            (self.cordelia, personal),
            (self.example_user("othello"), personal),
            (self.iago, other_channel),
        ]:
            self.assert_json_error(self.revoke(user, row), "No such channel email address.")
        self.assertEqual(
            ChannelEmailAddress.objects.filter(
                id__in=[bot.id, personal.id, other_channel.id]
            ).count(),
            3,
        )

        self.assert_json_success(self.revoke(self.iago, bot))
        self.assert_json_success(self.revoke(self.iago, personal))
        with self.assertRaises(ZulipEmailForwardError):
            validate_to_address(encoded, rate_limit=False)
        self.assert_json_error(self.revoke(self.iago, bot), "No such channel email address.")

        new_address = self.assert_json_success(self.generate(self.iago))["email"]
        self.assertNotEqual(new_address.split(".")[1], bot.email_token)

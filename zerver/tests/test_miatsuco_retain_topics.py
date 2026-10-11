from datetime import timedelta

from django.utils.timezone import now as timezone_now

from zerver.lib.retention import archive_messages
from zerver.models import Message, Stream
from zerver.tests.test_retention import ZULIP_REALM_DAYS, ArchiveMessagesTestingBase

TOPICS = ["alpha", "alpha", "Alpha", "beta", "beta"]


class MiatsucoRetainTopicsTest(ArchiveMessagesTestingBase):
    def make_subscribed_stream(self, name: str) -> Stream:
        stream = self.make_stream(name)
        self.subscribe(self.example_user("hamlet"), name)
        return stream

    def send_expired_topic_messages(self, stream: Stream, topics: list[str]) -> list[int]:
        sender = self.example_user("hamlet")
        message_ids = [
            self.send_stream_message(sender, stream.name, f"message {i}", topic_name=topic)
            for i, topic in enumerate(topics)
        ]
        self._change_messages_date_sent(
            message_ids, timezone_now() - timedelta(days=ZULIP_REALM_DAYS + 1)
        )
        return message_ids

    def remaining_message_ids(self, stream: Stream) -> list[int]:
        return list(
            Message.objects.filter(realm_id=stream.realm_id, recipient=stream.recipient)
            .order_by("id")
            .values_list("id", flat=True)
        )

    def test_oldest_message_survives(self) -> None:
        plain_stream = self.make_subscribed_stream("plain")
        channel_kept_stream = self.make_subscribed_stream("channel kept")
        channel_kept_stream.miatsuco_retain_topics = True
        channel_kept_stream.save(update_fields=["miatsuco_retain_topics"])

        self.send_expired_topic_messages(plain_stream, TOPICS)
        channel_kept_ids = self.send_expired_topic_messages(channel_kept_stream, TOPICS)

        archive_messages()
        self.assertEqual(self.remaining_message_ids(plain_stream), [])
        self.assertEqual(
            self.remaining_message_ids(channel_kept_stream),
            [channel_kept_ids[0], channel_kept_ids[3]],
        )

        self.zulip_realm.miatsuco_retain_topics = True
        self.zulip_realm.save(update_fields=["miatsuco_retain_topics"])
        plain_ids = self.send_expired_topic_messages(plain_stream, TOPICS)

        archive_messages()
        self.assertEqual(self.remaining_message_ids(plain_stream), [plain_ids[0], plain_ids[3]])
        self.assertEqual(
            self.remaining_message_ids(channel_kept_stream),
            [channel_kept_ids[0], channel_kept_ids[3]],
        )

    def test_oldest_message_after_move(self) -> None:
        stream = self.make_subscribed_stream("kept")
        stream.miatsuco_retain_topics = True
        stream.save(update_fields=["miatsuco_retain_topics"])

        gamma_id, beta_first_id, _beta_second_id = self.send_expired_topic_messages(
            stream, ["gamma", "beta", "beta"]
        )
        archive_messages()
        self.assertEqual(self.remaining_message_ids(stream), [gamma_id, beta_first_id])

        self.login("iago")
        result = self.client_patch(
            f"/json/messages/{gamma_id}",
            {"topic": "beta", "propagate_mode": "change_one"},
        )
        self.assert_json_success(result)

        archive_messages()
        remaining_ids = self.remaining_message_ids(stream)
        self.assertIn(gamma_id, remaining_ids)
        self.assertNotIn(beta_first_id, remaining_ids)

    def test_stream_setting_requires_channel_administrator(self) -> None:
        stream = self.make_subscribed_stream("kept")
        self._set_realm_message_retention_value(self.zulip_realm, ZULIP_REALM_DAYS)
        setting = {"miatsuco_retain_topics": "true"}

        self.login("hamlet")
        result = self.client_patch(f"/json/streams/{stream.id}", setting)
        self.assert_json_error(result, "You do not have permission to administer this channel.")

        self.login("iago")
        result = self.client_patch(f"/json/streams/{stream.id}", setting)
        self.assert_json_success(result)

        stream.refresh_from_db()
        self.assertTrue(stream.miatsuco_retain_topics)

    def test_setting_requires_retention(self) -> None:
        error = "Retaining topics requires a message retention period."
        stream = self.make_subscribed_stream("kept")
        setting = {"miatsuco_retain_topics": "true"}
        self._set_realm_message_retention_value(self.zulip_realm, -1)

        self.login("desdemona")
        result = self.client_patch("/json/realm", setting)
        self.assert_json_error(result, error)
        result = self.client_patch(f"/json/streams/{stream.id}", setting)
        self.assert_json_error(result, error)

        result = self.client_patch("/json/realm", {**setting, "message_retention_days": "10"})
        self.assert_json_success(result)
        result = self.client_patch(
            "/json/realm", {**setting, "message_retention_days": '"unlimited"'}
        )
        self.assert_json_error(result, error)

        self.zulip_realm.refresh_from_db()
        self.assertEqual(self.zulip_realm.message_retention_days, 10)
        self.assertTrue(self.zulip_realm.miatsuco_retain_topics)

        result = self.client_patch("/json/realm", {"message_retention_days": '"unlimited"'})
        self.assert_json_error(result, error)

        result = self.client_patch(f"/json/streams/{stream.id}", setting)
        self.assert_json_success(result)

        result = self.client_patch(
            f"/json/streams/{stream.id}", {"message_retention_days": '"unlimited"'}
        )
        self.assert_json_error(result, error)

        self._set_stream_message_retention_value(stream, -1)
        result = self.client_patch(
            f"/json/streams/{stream.id}", {"miatsuco_retain_topics": "false"}
        )
        self.assert_json_success(result)
        result = self.client_patch(f"/json/streams/{stream.id}", setting)
        self.assert_json_error(result, error)

        self._set_stream_message_retention_value(stream, 20)
        self._set_realm_message_retention_value(self.zulip_realm, -1)
        result = self.client_patch(f"/json/streams/{stream.id}", setting)
        self.assert_json_success(result)

    def test_changing_retention_and_setting_together(self) -> None:
        stream = self.make_subscribed_stream("kept")
        self._set_realm_message_retention_value(self.zulip_realm, ZULIP_REALM_DAYS)
        setting = {"miatsuco_retain_topics": "true"}

        self.login("iago")
        result = self.client_patch(
            f"/json/streams/{stream.id}", {**setting, "message_retention_days": '"unlimited"'}
        )
        self.assert_json_error(result, "Retaining topics requires a message retention period.")

        result = self.client_patch(
            f"/json/streams/{stream.id}", {**setting, "message_retention_days": "30"}
        )
        self.assert_json_success(result)
        stream.refresh_from_db()
        self.assertTrue(stream.miatsuco_retain_topics)
        self.assertEqual(stream.message_retention_days, 30)

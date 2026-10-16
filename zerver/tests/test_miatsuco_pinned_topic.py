from zerver.actions.streams import do_change_stream_group_based_setting
from zerver.actions.user_groups import check_add_user_group
from zerver.lib.exceptions import JsonableError
from zerver.lib.test_miatsuco import MiatsucoPinnedTopicTestMixin
from zerver.lib.topic import messages_for_topic
from zerver.models.streams import get_stream

PIN = "📌 "
RESOLVED = "✔ "
MOVE_ERROR = "Messages can't be moved into or out of a pinned topic."
ADMIN_ERROR = "Only channel administrators can pin, unpin, or rename a pinned topic."


class MiatsucoPinnedTopicTest(MiatsucoPinnedTopicTestMixin):
    def get_message_dict(self, message_id: int) -> dict[str, object]:
        result = self.client_get(f"/json/messages/{message_id}")
        message = self.assert_json_success(result)["message"]
        assert isinstance(message, dict)
        return message

    def assert_notice(self, topic_name: str, text: str) -> None:
        notice = self.get_last_message()
        self.assertEqual(notice.topic_name(), topic_name)
        self.assertEqual(notice.sender.email, "notification-bot@zulip.com")
        self.assertIn(text, notice.content)

    def test_pinning_and_unpinning(self) -> None:
        first = self.send("plans")
        self.send("plans", self.member)
        self.login_user(self.admin)

        self.assert_json_success(self.edit_topic(first, f"{PIN}plans"))
        self.assertIn(f"{PIN}plans", self.topic_names())
        self.assertNotIn("plans", self.topic_names())
        self.assert_notice(f"{PIN}plans", "has pinned this topic.")
        self.assertNotIn("last_moved_timestamp", self.get_message_dict(first))

        self.assert_json_success(self.edit_topic(first, "plans"))
        self.assertIn("plans", self.topic_names())
        self.assertNotIn(f"{PIN}plans", self.topic_names())
        self.assert_notice("plans", "has unpinned this topic.")
        self.assertNotIn("last_moved_timestamp", self.get_message_dict(first))

        self.assert_json_success(self.edit_topic(first, f"{PIN}schedule"))
        self.assert_notice(f"{PIN}schedule", "has pinned this topic.")
        self.assert_json_success(self.edit_topic(first, f"{PIN}new schedule"))
        self.assertIn(f"{PIN}new schedule", self.topic_names())
        self.assertNotIn("has unpinned", self.get_last_message().content)
        self.assert_json_success(self.edit_topic(first, "agenda"))
        self.assert_notice("agenda", "has unpinned this topic.")

    def test_permissions(self) -> None:
        with self.assertRaisesRegex(
            JsonableError, "Only channel administrators can start a pinned topic."
        ):
            self.send(f"{PIN}fresh", self.member)
        self.send(f"{PIN}fresh")
        self.send(f"{PIN}fresh", self.member)

        first = self.send("plans", self.member)
        self.login_user(self.member)
        self.assert_json_error(self.edit_topic(first, f"{PIN}plans"), ADMIN_ERROR)
        self.login_user(self.admin)
        self.assert_json_success(self.edit_topic(first, f"{PIN}plans"))
        self.login_user(self.member)
        for topic_name in ["plans", f"{PIN}renamed"]:
            self.assert_json_error(self.edit_topic(first, topic_name), ADMIN_ERROR)

        stream = get_stream(self.stream_name, self.admin.realm)
        group = check_add_user_group(
            self.admin.realm, "channel admins", [self.member], acting_user=self.admin
        )
        do_change_stream_group_based_setting(
            stream, "can_administer_channel_group", group, acting_user=self.admin
        )
        self.assert_json_success(self.edit_topic(first, f"{PIN}renamed"))
        self.assert_json_success(self.edit_topic(first, "renamed"))

    def test_second_pin_unpins_the_first(self) -> None:
        first = self.send("plans")
        second = self.send("chores")
        self.login_user(self.admin)
        self.assert_json_success(self.edit_topic(first, f"{PIN}plans"))
        self.assert_json_success(self.edit_topic(second, f"{PIN}chores"))
        self.assertIn(f"{PIN}chores", self.topic_names())
        self.assertIn("plans", self.topic_names())
        self.assertNotIn(f"{PIN}plans", self.topic_names())
        stream = get_stream(self.stream_name, self.admin.realm)
        assert stream.recipient_id is not None
        unpin_notices = messages_for_topic(stream.realm_id, stream.recipient_id, "plans").filter(
            content__contains="has unpinned this topic."
        )
        self.assertEqual(unpin_notices.count(), 1)

        third = self.send("agenda")
        self.send("chores")
        result = self.edit_topic(third, f"{PIN}agenda")
        self.assert_json_error(
            result,
            "The channel's pinned topic can't be unpinned because the topic chores already exists.",
        )
        self.assertTrue({f"{PIN}chores", "chores", "agenda"} <= self.topic_names())
        self.assertNotIn(f"{PIN}agenda", self.topic_names())

    def test_messages_cannot_move_into_or_out_of_a_pinned_topic(self) -> None:
        first = self.send("plans")
        self.send("plans")
        other = self.send("chores")
        self.login_user(self.admin)
        for propagate_mode in ["change_one", "change_later"]:
            result = self.edit_topic(first, f"{PIN}plans", propagate_mode)
            self.assert_json_error(result, MOVE_ERROR)
        self.assertNotIn(f"{PIN}plans", self.topic_names())

        self.assert_json_success(self.edit_topic(first, f"{PIN}plans"))
        stream = get_stream(self.stream_name, self.admin.realm)
        assert stream.recipient_id is not None
        pinned_message = (
            messages_for_topic(stream.realm_id, stream.recipient_id, f"{PIN}plans")
            .order_by("id")
            .first()
        )
        assert pinned_message is not None

        self.assert_json_error(
            self.edit_topic(pinned_message.id, "chores", "change_one"), MOVE_ERROR
        )
        self.assert_json_error(self.edit_topic(other, f"{PIN}plans", "change_one"), MOVE_ERROR)
        self.assert_json_error(self.edit_topic(other, f"{PIN}plans"), MOVE_ERROR)
        verona = get_stream("Verona", self.admin.realm)
        result = self.client_patch(
            f"/json/messages/{pinned_message.id}",
            {"stream_id": verona.id, "propagate_mode": "change_all"},
        )
        self.assert_json_error(result, MOVE_ERROR)

        self.send("plans")
        for topic_name in ["plans", "Plans"]:
            self.assert_json_error(self.edit_topic(first, topic_name), MOVE_ERROR)
        self.assertIn(f"{PIN}plans", self.topic_names())

    def test_pinned_and_resolved_are_exclusive(self) -> None:
        for topic_name in [f"{PIN}{RESOLVED}x", f"{RESOLVED}{PIN}x"]:
            with self.assertRaisesRegex(
                JsonableError, "A topic can't be both pinned and resolved."
            ):
                self.send(topic_name)

        pinned = self.send("plans")
        resolved = self.send("chores")
        self.login_user(self.admin)
        self.assert_json_success(self.edit_topic(pinned, f"{PIN}plans"))
        self.assert_json_success(self.edit_topic(resolved, f"{RESOLVED}chores"))
        for message_id, topic_name in [
            (pinned, f"{RESOLVED}{PIN}plans"),
            (resolved, f"{PIN}{RESOLVED}chores"),
        ]:
            result = self.edit_topic(message_id, topic_name)
            self.assert_json_error(result, "A topic can't be both pinned and resolved.")

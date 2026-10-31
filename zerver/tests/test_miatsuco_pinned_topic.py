from zerver.actions.streams import do_change_stream_group_based_setting
from zerver.actions.user_groups import check_add_user_group
from zerver.lib.exceptions import JsonableError
from zerver.lib.message import truncate_topic
from zerver.lib.test_miatsuco import MiatsucoPinnedTopicTestMixin
from zerver.lib.topic import messages_for_topic
from zerver.models.streams import get_stream

PIN = "📌 "
RESOLVED = "✔ "
CHANNEL_MOVE_ERROR = "Pinned topics can't be moved to another channel."
WHOLE_TOPIC_ERROR = "Pinning, unpinning, or renaming a pinned topic must apply to the whole topic."
TOPIC_EXISTS_ERROR = f"The topic {PIN}plans already exists."
PLAIN_TOPIC_EXISTS_ERROR = "The topic plans already exists."
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
        self.assert_json_success(self.edit_topic(first, f"{PIN}New schedule"))
        self.assertIn(f"{PIN}New schedule", self.topic_names())
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

    def test_messages_cannot_move_into_or_out_of_a_pinned_topic(self) -> None:
        first = self.send("plans")
        self.send("plans")
        other = self.send("chores")
        self.login_user(self.admin)
        for propagate_mode in ["change_one", "change_later"]:
            result = self.edit_topic(first, f"{PIN}plans", propagate_mode)
            self.assert_json_error(result, WHOLE_TOPIC_ERROR)
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
            self.edit_topic(pinned_message.id, "chores", "change_one"), WHOLE_TOPIC_ERROR
        )
        self.assert_json_error(
            self.edit_topic(other, f"{PIN}plans", "change_one"), WHOLE_TOPIC_ERROR
        )
        self.assert_json_error(self.edit_topic(other, f"{PIN}plans"), TOPIC_EXISTS_ERROR)
        verona = get_stream("Verona", self.admin.realm)
        result = self.client_patch(
            f"/json/messages/{pinned_message.id}",
            {"stream_id": verona.id, "propagate_mode": "change_all"},
        )
        self.assert_json_error(result, CHANNEL_MOVE_ERROR)

    def test_a_topic_and_its_pinned_form_cannot_both_exist(self) -> None:
        first = self.send("plans")
        other = self.send("chores")
        self.login_user(self.admin)
        self.assert_json_success(self.edit_topic(first, f"{PIN}plans"))

        self.send("plans", self.member)
        self.assertEqual(self.get_last_message().topic_name(), f"{PIN}plans")
        self.assertNotIn("plans", self.topic_names())
        self.assert_json_error(self.edit_topic(other, "plans"), TOPIC_EXISTS_ERROR)

        group = check_add_user_group(self.admin.realm, "no posters", [], acting_user=self.admin)
        stream = get_stream(self.stream_name, self.admin.realm)
        do_change_stream_group_based_setting(
            stream, "miatsuco_can_post_in_pinned_topic_group", group, acting_user=self.admin
        )
        with self.assertRaisesRegex(
            JsonableError, "You do not have permission to post in the pinned topic."
        ):
            self.send("plans", self.member)

        self.assert_json_success(self.edit_topic(first, "plans"))
        self.send(f"{PIN}plans")
        self.assertEqual(self.get_last_message().topic_name(), "plans")
        self.assertNotIn(f"{PIN}plans", self.topic_names())
        self.assert_json_error(self.edit_topic(other, f"{PIN}plans"), PLAIN_TOPIC_EXISTS_ERROR)

    def test_a_topic_at_the_length_limit_resolves_to_its_pinned_form(self) -> None:
        long_name = "a" * 60
        first = self.send(long_name)
        other = self.send("chores")
        self.login_user(self.admin)
        self.assert_json_success(self.edit_topic(first, PIN + long_name))
        pinned_name = truncate_topic(PIN + long_name)
        self.assertIn(pinned_name, self.topic_names())

        self.send(long_name, self.member)
        self.assertEqual(self.get_last_message().topic_name(), pinned_name)
        self.assertNotIn(long_name, self.topic_names())
        self.assert_json_error(
            self.edit_topic(other, long_name), f"The topic {pinned_name} already exists."
        )

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

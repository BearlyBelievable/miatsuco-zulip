from zerver.actions.streams import do_change_stream_group_based_setting
from zerver.actions.user_groups import check_add_user_group
from zerver.lib.exceptions import JsonableError
from zerver.lib.test_miatsuco import MiatsucoPinnedTopicTestMixin
from zerver.models import NamedUserGroup
from zerver.models.groups import SystemGroups
from zerver.models.streams import get_stream

PIN = "📌 "


class MiatsucoPinnedTopicPostGroupTest(MiatsucoPinnedTopicTestMixin):
    def set_post_group(self, name: str) -> None:
        stream = get_stream(self.stream_name, self.admin.realm)
        group = NamedUserGroup.objects.get(
            name=name, realm_for_sharding=self.admin.realm, is_system_group=True
        )
        do_change_stream_group_based_setting(
            stream, "miatsuco_can_post_in_pinned_topic_group", group, acting_user=self.admin
        )

    def test_posting_in_the_pinned_topic_requires_the_group(self) -> None:
        stream = get_stream(self.stream_name, self.admin.realm)
        self.assertEqual(
            stream.miatsuco_can_post_in_pinned_topic_group.named_user_group.name,
            SystemGroups.EVERYONE,
        )
        self.send(f"{PIN}fresh")
        message_id = self.send(f"{PIN}fresh", self.member)

        self.set_post_group(SystemGroups.ADMINISTRATORS)
        error = "You do not have permission to post in the pinned topic."
        with self.assertRaisesRegex(JsonableError, error):
            self.send(f"{PIN}fresh", self.member)
        self.send(f"{PIN}fresh")
        self.send("plans", self.member)

        self.login_user(self.member)
        result = self.client_patch(f"/json/messages/{message_id}", {"content": "edited"})
        self.assert_json_error(result, error)
        self.set_post_group(SystemGroups.EVERYONE)
        result = self.client_patch(f"/json/messages/{message_id}", {"content": "edited"})
        self.assert_json_success(result)

        self.set_post_group(SystemGroups.NOBODY)
        chores = self.send("chores")
        self.login_user(self.admin)
        self.assert_json_success(self.edit_topic(chores, f"{PIN}chores"))
        self.assertIn(f"{PIN}chores", self.topic_names())
        self.assert_json_success(self.edit_topic(chores, "chores"))

    def test_posting_with_a_custom_group(self) -> None:
        stream = get_stream(self.stream_name, self.admin.realm)
        group = check_add_user_group(
            self.admin.realm, "pin posters", [self.admin, self.member], acting_user=self.admin
        )
        do_change_stream_group_based_setting(
            stream, "miatsuco_can_post_in_pinned_topic_group", group, acting_user=self.admin
        )

        self.send(f"{PIN}fresh")
        self.send(f"{PIN}fresh", self.member)
        with self.assertRaisesRegex(
            JsonableError, "You do not have permission to post in the pinned topic."
        ):
            self.send(f"{PIN}fresh", self.example_user("cordelia"))

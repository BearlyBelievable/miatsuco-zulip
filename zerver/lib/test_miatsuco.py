# nocoverage
#
# The bare "# nocoverage" line above excludes this whole module from
# backend coverage enforcement (see tools/coveragerc). This module
# provides shared test *support* (a helper mixin), not tests of its
# own. Its methods are exercised by each feature's test module
# (zerver/tests/test_miatsuco_<feature>.py) once those land, not by
# this file directly, so on a baseline that ships ahead of any feature
# it has no coverage of its own. Upstream marks comparable helper code
# in zerver/lib/test_classes.py and test_helpers.py the same way. When
# feature tests that call every helper here are present, this marker
# can be removed so the helpers are held to real coverage through their
# callers.
import re
from typing import TYPE_CHECKING

import orjson
from typing_extensions import override

from zerver.actions.create_user import do_create_user
from zerver.actions.realm_settings import do_change_realm_permission_group_setting
from zerver.lib.test_classes import ZulipTestCase
from zerver.lib.upload import upload_message_attachment
from zerver.models import Message, NamedUserGroup, UserProfile
from zerver.models.realms import get_realm
from zerver.models.streams import get_stream

if TYPE_CHECKING:
    from django.test.client import _MonkeyPatchedWSGIResponse as TestHttpResponse

# Shared test support for MiAtSu.Co fork-specific features.
#
# This lives in zerver/lib/ (not zerver/tests/) on purpose, following
# upstream Zulip's own convention of keeping reusable test base
# classes in zerver/lib/test_classes.py rather than in the test
# modules themselves. The backend test runner only discovers modules
# under zerver/tests/, so a helper module here is never mistaken for a
# test module (upstream keeps test_classes.py, test_helpers.py, and
# others here for the same reason).
#
# Each fork feature gets its own test module named for that feature,
# zerver/tests/test_miatsuco_<feature>.py, and imports
# MiatsucoMarkdownTestMixin from here. This is deliberate: because no
# two feature branches ever edit the same file, each feature's tests
# apply cleanly and independently, in any order, with no merge
# conflict between them -- which matters both for this fork's own
# stacked feature patches and for anyone developing a feature branch
# independently. Adding a new feature's tests never requires touching
# this file or any other feature's test file.
#
# The upload_file_and_get_path_id() helper below exists so the common
# "upload a file, then derive its path_id" pattern doesn't require
# every feature's test module to re-import re and
# upload_message_attachment. If a feature needs a new shared helper,
# add it here; if a helper is specific to one feature, keep it in that
# feature's own test module.
#
# See docs/contributing/miatsuco-fork-conventions.md for the full
# rationale.


class MiatsucoMarkdownTestMixin(ZulipTestCase):
    def assert_message_content_is(
        self, message_id: int, rendered_content: str, user_name: str = "othello"
    ) -> None:
        sender_user_profile = self.example_user(user_name)
        result = self.assert_json_success(
            self.api_get(sender_user_profile, f"/api/v1/messages/{message_id}")
        )
        self.assertEqual(result["message"]["content"], rendered_content)

    def send_message_content(self, content: str, user_name: str = "othello") -> int:
        sender_user_profile = self.example_user(user_name)
        return self.send_stream_message(
            sender=sender_user_profile,
            stream_name="Verona",
            content=content,
        )

    def upload_file_and_get_path_id(
        self, filename: str, content_type: str, contents: bytes = b"", user_name: str = "othello"
    ) -> tuple[str, str]:
        url = upload_message_attachment(
            filename,
            content_type,
            contents,
            self.example_user(user_name),
        )[0]
        path_id = re.sub(r"/user_uploads/", "", url)
        return url, path_id


class MiatsucoUserManagementTestMixin(ZulipTestCase):
    DENIED_ERROR = "Insufficient permission"
    OWNER_ONLY_ERROR = "Must be an organization owner"

    def set_realm_group_setting(self, setting_name: str, group_name: str) -> None:
        realm = get_realm("zulip")
        group = NamedUserGroup.objects.get(
            name=group_name, realm_for_sharding=realm, is_system_group=True
        )
        do_change_realm_permission_group_setting(realm, setting_name, group, acting_user=None)

    def api_deactivate_user(self, user: UserProfile) -> "TestHttpResponse":
        return self.client_delete(f"/json/users/{user.id}")

    def api_reactivate_user(self, user: UserProfile) -> "TestHttpResponse":
        return self.client_post(f"/json/users/{user.id}/reactivate")

    def api_patch_user(self, user: UserProfile, **data: str) -> "TestHttpResponse":
        return self.client_patch(f"/json/users/{user.id}", data)

    def api_set_user_role(self, user: UserProfile, role: int) -> "TestHttpResponse":
        return self.api_patch_user(user, role=orjson.dumps(role).decode())

    def create_bot(self) -> UserProfile:
        return do_create_user(
            "bot@zulip.com",
            "password",
            get_realm("zulip"),
            "Some bot",
            bot_type=UserProfile.DEFAULT_BOT,
            bot_owner=self.example_user("hamlet"),
            acting_user=None,
        )


class MiatsucoPinnedTopicTestMixin(ZulipTestCase):
    @override
    def setUp(self) -> None:
        super().setUp()
        self.stream_name = "Denmark"
        self.admin = self.example_user("iago")
        self.member = self.example_user("hamlet")

    def send(self, topic_name: str, sender: UserProfile | None = None) -> int:
        return self.send_stream_message(
            sender or self.admin, self.stream_name, topic_name=topic_name
        )

    def edit_topic(
        self,
        message_id: int,
        topic_name: str,
        propagate_mode: str = "change_all",
    ) -> "TestHttpResponse":
        return self.client_patch(
            f"/json/messages/{message_id}",
            {
                "topic": topic_name,
                "propagate_mode": propagate_mode,
                "send_notification_to_old_thread": "false",
                "send_notification_to_new_thread": "false",
            },
        )

    def topic_names(self) -> set[str]:
        stream = get_stream(self.stream_name, self.admin.realm)
        assert stream.recipient_id is not None
        return {
            message.topic_name()
            for message in Message.objects.filter(
                realm_id=stream.realm_id, recipient_id=stream.recipient_id, is_channel_message=True
            )
        }

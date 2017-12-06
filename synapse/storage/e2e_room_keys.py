# -*- coding: utf-8 -*-
# Copyright 2017 New Vector Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from twisted.internet import defer

from ._base import SQLBaseStore


class EndToEndRoomKeyStore(SQLBaseStore):

    @defer.inlineCallbacks
    def get_e2e_room_key(self, user_id, version, room_id, session_id):

        row = yield self._simple_select_one(
            table="e2e_room_keys",
            keyvalues={
                "user_id": user_id,
                "version": version,
                "room_id": room_id,
                "session_id": session_id,
            },
            retcols=(
                "first_message_index",
                "forwarded_count",
                "is_verified",
                "session_data",
            ),
            desc="get_e2e_room_key",
        )

        defer.returnValue(row)

    def set_e2e_room_key(self, user_id, version, room_id, session_id, room_key):

        def _set_e2e_room_key_txn(txn):

            self._simple_upsert_txn(
                txn,
                table="e2e_room_keys",
                keyvalues={
                    "user_id": user_id,
                    "room_id": room_id,
                    "session_id": session_id,
                },
                values={
                    "version": version,
                    "first_message_index": room_key['first_message_index'],
                    "forwarded_count": room_key['forwarded_count'],
                    "is_verified": room_key['is_verified'],
                    "session_data": room_key['session_data'],
                },
                lock=False,
            )

            return True

        return self.runInteraction(
            "set_e2e_room_key", _set_e2e_room_key_txn
        )

    # XXX: this isn't currently used and isn't tested anywhere
    # it could be used in future for bulk-uploading new versions of room_keys
    # for a user or something though.
    def set_e2e_room_keys(self, user_id, version, room_keys):

        def _set_e2e_room_keys_txn(txn):

            values = []
            for room_id in room_keys['rooms']:
                for session_id in room_keys['rooms'][room_id]['sessions']:
                    session = room_keys['rooms'][room_id]['sessions'][session_id]
                    values.append(
                        {
                            "user_id": user_id,
                            "room_id": room_id,
                            "session_id": session_id,
                            "version": version,
                            "first_message_index": session['first_message_index'],
                            "forwarded_count": session['forwarded_count'],
                            "is_verified": session['is_verified'],
                            "session_data": session['session_data'],
                        }
                    )

            self._simple_insert_many_txn(
                txn,
                table="e2e_room_keys",
                values=values
            )

            return True

        return self.runInteraction(
            "set_e2e_room_keys", _set_e2e_room_keys_txn
        )

    @defer.inlineCallbacks
    def get_e2e_room_keys(self, user_id, version, room_id, session_id):

        keyvalues = {
            "user_id": user_id,
            "version": version,
        }
        if room_id:
            keyvalues['room_id'] = room_id
        if session_id:
            keyvalues['session_id'] = session_id

        rows = yield self._simple_select_list(
            table="e2e_room_keys",
            keyvalues=keyvalues,
            retcols=(
                "user_id",
                "room_id",
                "session_id",
                "first_message_index",
                "forwarded_count",
                "is_verified",
                "session_data",
            ),
            desc="get_e2e_room_keys",
        )

        # perlesque autovivification from https://stackoverflow.com/a/19829714/6764493
        class AutoVivification(dict):
            def __getitem__(self, item):
                try:
                    return dict.__getitem__(self, item)
                except KeyError:
                    value = self[item] = type(self)()
                    return value

        sessions = AutoVivification()
        for row in rows:
            sessions['rooms'][row['room_id']]['sessions'][row['session_id']] = {
                "first_message_index": row["first_message_index"],
                "forwarded_count": row["forwarded_count"],
                "is_verified": row["is_verified"],
                "session_data": row["session_data"],
            }

        defer.returnValue(sessions)

    @defer.inlineCallbacks
    def delete_e2e_room_keys(self, user_id, version, room_id, session_id):

        keyvalues = {
            "user_id": user_id,
            "version": version,
        }
        if room_id:
            keyvalues['room_id'] = room_id
        if session_id:
            keyvalues['session_id'] = session_id

        yield self._simple_delete(
            table="e2e_room_keys",
            keyvalues=keyvalues,
            desc="delete_e2e_room_keys",
        )

    @defer.inlineCallbacks
    def get_e2e_room_key_version(self, user_id, version):

        row = yield self._simple_select_one(
            table="e2e_room_key_versions",
            keyvalues={
                "user_id": user_id,
                "version": version,
            },
            retcols=(
                "user_id",
                "version",
                "algorithm",
                "auth_data",
            ),
            desc="get_e2e_room_key_version_info",
        )

        defer.returnValue(row)

    def create_e2e_room_key_version(self, user_id, version, info):

        def _create_e2e_room_key_version_txn(txn):

            self._simple_insert_txn(
                txn,
                table="e2e_room_key_versions",
                values={
                    "user_id": user_id,
                    "version": version,
                    "algorithm": info["algorithm"],
                    "auth_data": info["auth_data"],
                },
                lock=False,
            )

            return True

        return self.runInteraction(
            "create_e2e_room_key_version_txn", _create_e2e_room_key_version_txn
        )

    @defer.inlineCallbacks
    def delete_e2e_room_key_version(self, user_id, version):

        keyvalues = {
            "user_id": user_id,
            "version": version,
        }

        yield self._simple_delete(
            table="e2e_room_key_versions",
            keyvalues=keyvalues,
            desc="delete_e2e_room_key_version",
        )

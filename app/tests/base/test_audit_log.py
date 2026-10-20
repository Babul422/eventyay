import pytest
from django.utils.timezone import now
from django_scopes import scope, scopes_disabled

from eventyay.base.models import Event, Organizer, User
from eventyay.base.models.audit import AuditLog
from eventyay.base.services.event import _create_room, get_audit_log


@pytest.mark.django_db
def test_audit_log_serialize_public_with_null_user():
    """Verify that AuditLog.serialize_public() serializes user as None when user is None."""
    with scopes_disabled():
        organizer = Organizer.objects.create(name='Audit Org', slug='audit-org-null')
        event = Event.objects.create(
            organizer=organizer, name='Audit Event', slug='audit-event-null', date_from=now()
        )

    with scope(event=event):
        log = AuditLog.objects.create(
            event=event,
            user=None,
            type='system.maintenance',
            data={'action': 'cleanup'},
        )

        serialized = log.serialize_public()
        assert serialized['id'] == log.id
        assert serialized['user'] is None
        assert serialized['type'] == 'system.maintenance'
        assert serialized['data'] == {'action': 'cleanup'}


@pytest.mark.django_db
def test_audit_log_serialize_public_with_active_user():
    """Verify that AuditLog.serialize_public() retains normal user serialization for active users."""
    with scopes_disabled():
        organizer = Organizer.objects.create(name='Audit Org', slug='audit-org-user')
        event = Event.objects.create(
            organizer=organizer, name='Audit Event', slug='audit-event-user', date_from=now()
        )
        user = User.objects.create(email='active_auditor@example.com')

    with scope(event=event):
        log = AuditLog.objects.create(
            event=event,
            user=user,
            type='auth.user.updated',
            data={'status': 'ok'},
        )

        serialized = log.serialize_public()
        assert serialized['id'] == log.id
        assert serialized['user'] is not None
        assert serialized['user']['id'] == str(user.id)
        assert serialized['type'] == 'auth.user.updated'


@pytest.mark.django_db
def test_create_room_with_creator_none_serializes_cleanly():
    """Verify that _create_room(creator=None) creates an AuditLog that serializes safely."""
    with scopes_disabled():
        organizer = Organizer.objects.create(name='Room Org', slug='room-org-null')
        event = Event.objects.create(
            organizer=organizer, name='Room Event', slug='room-event-null', date_from=now()
        )

    with scope(event=event):
        create_room_fn = getattr(_create_room, 'func', _create_room)
        room, _ = create_room_fn(
            data={'event': event, 'name': 'Main Track Room'},
            with_channel=True,
            creator=None,
        )

        audit_entry = AuditLog.objects.filter(event=event, type='event.room.added').first()
        assert audit_entry is not None
        assert audit_entry.user is None

        serialized = audit_entry.serialize_public()
        assert serialized['user'] is None
        assert serialized['data']['object'] == str(room.id)


@pytest.mark.django_db
def test_get_audit_log_retrieves_multiple_entries_with_null_user():
    """Verify that get_audit_log(event) successfully returns all entries when one has user=None."""
    with scopes_disabled():
        organizer = Organizer.objects.create(name='Batch Org', slug='batch-org-mixed')
        event = Event.objects.create(
            organizer=organizer, name='Batch Event', slug='batch-event-mixed', date_from=now()
        )
        user1 = User.objects.create(email='u1_mixed@example.com')
        user2 = User.objects.create(email='u2_mixed@example.com')

    with scope(event=event):
        AuditLog.objects.create(event=event, user=user1, type='event.updated', data={'step': 1})
        AuditLog.objects.create(event=event, user=None, type='event.room.added', data={'step': 2})
        AuditLog.objects.create(event=event, user=user2, type='room.updated', data={'step': 3})

        audit_fn = getattr(get_audit_log, 'func', get_audit_log)
        results = audit_fn(event)

        assert len(results) == 3
        # Check that the null-user entry serializes as user: None while others have user objects
        serialized_by_type = {entry['type']: entry for entry in results}
        assert serialized_by_type['event.updated']['user']['id'] == str(user1.id)
        assert serialized_by_type['event.room.added']['user'] is None
        assert serialized_by_type['room.updated']['user']['id'] == str(user2.id)


@pytest.mark.django_db
def test_user_deletion_cascades_to_null_and_preserves_audit_log():
    """Verify that deleting a user sets AuditLog.user to NULL and get_audit_log continues to function."""
    with scopes_disabled():
        organizer = Organizer.objects.create(name='Del Org', slug='del-org-cascade')
        event = Event.objects.create(
            organizer=organizer, name='Del Event', slug='del-event-cascade', date_from=now()
        )
        user = User.objects.create(email='deleted_auditor@example.com')

    with scope(event=event):
        log = AuditLog.objects.create(
            event=event, user=user, type='auth.user.banned', data={'reason': 'abuse'}
        )

        audit_fn = getattr(get_audit_log, 'func', get_audit_log)
        initial_results = audit_fn(event)
        assert len(initial_results) == 1
        assert initial_results[0]['user']['id'] == str(user.id)

    # Delete user outside event scope (global model)
    with scopes_disabled():
        user.delete()

    with scope(event=event):
        log.refresh_from_db()
        assert log.user is None

        # Verify get_audit_log still succeeds and reports user as None
        post_delete_results = audit_fn(event)
        assert len(post_delete_results) == 1
        assert post_delete_results[0]['id'] == log.id
        assert post_delete_results[0]['user'] is None

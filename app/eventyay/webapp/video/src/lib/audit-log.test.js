import test from 'node:test'
import assert from 'node:assert/strict'
import { getAuditLogUserDisplay, filterAuditLogEntries } from './audit-log.js'

test('getAuditLogUserDisplay returns display name when present', () => {
	const user = { id: 123, profile: { display_name: 'Alice' } }
	assert.equal(getAuditLogUserDisplay(user), 'Alice')
})

test('getAuditLogUserDisplay falls back to user ID when display name is missing', () => {
	const userWithNoProfile = { id: 456 }
	assert.equal(getAuditLogUserDisplay(userWithNoProfile), '456')

	const userWithEmptyName = { id: 789, profile: { display_name: '' } }
	assert.equal(getAuditLogUserDisplay(userWithEmptyName), '789')
})

test('getAuditLogUserDisplay displays System / Deleted fallback in list and details modal when user is null', () => {
	assert.equal(getAuditLogUserDisplay(null), 'System / Deleted')
	assert.equal(getAuditLogUserDisplay(undefined), 'System / Deleted')
	assert.equal(getAuditLogUserDisplay(null, 'Localized Fallback'), 'Localized Fallback')
})

test('filterAuditLogEntries retains null-user entry when searching for the fallback label', () => {
	const entries = [
		{ id: 1, user: null, type: 'event.room.added', data: {} },
		{ id: 2, user: { id: 10, profile: { display_name: 'Bob' } }, type: 'event.updated', data: {} }
	]
	const matchedBySystem = filterAuditLogEntries(entries, 'System')
	assert.equal(matchedBySystem.length, 1)
	assert.equal(matchedBySystem[0].id, 1)

	const matchedByDeleted = filterAuditLogEntries(entries, 'deleted')
	assert.equal(matchedByDeleted.length, 1)
	assert.equal(matchedByDeleted[0].id, 1)
})

test('filterAuditLogEntries retains entry when searching for visible user ID when display name is missing', () => {
	const entries = [
		{ id: 1, user: { id: 'usr_xyz123' }, type: 'event.room.added', data: {} },
		{ id: 2, user: { id: 'usr_abc456', profile: { display_name: 'Charlie' } }, type: 'event.updated', data: {} }
	]
	const matchedById = filterAuditLogEntries(entries, 'xyz123')
	assert.equal(matchedById.length, 1)
	assert.equal(matchedById[0].id, 1)

	const matchedByDisplayName = filterAuditLogEntries(entries, 'Charlie')
	assert.equal(matchedByDisplayName.length, 1)
	assert.equal(matchedByDisplayName[0].id, 2)
})

export function getAuditLogUserDisplay(user, fallbackLabel = 'System / Deleted') {
	if (!user) return fallbackLabel
	return user.profile?.display_name || (user.id ? String(user.id) : '')
}

export function filterAuditLogEntries(entries, search, fallbackLabel = 'System / Deleted') {
	if (!entries) return
	if (!search) return entries
	const query = search.toLowerCase()
	return entries.filter(entry => {
		if (entry.user) {
			const userIdentifier = getAuditLogUserDisplay(entry.user, '')
			if (userIdentifier.toLowerCase().includes(query)) return true
		} else {
			const fallback = (fallbackLabel || '').toLowerCase()
			if (fallback.includes(query) || 'system / deleted'.includes(query)) return true
		}
		if (entry.type?.toLowerCase().startsWith(query)) return true
		if (JSON.stringify(entry.data)?.toLowerCase().includes(query)) return true
		return false
	})
}

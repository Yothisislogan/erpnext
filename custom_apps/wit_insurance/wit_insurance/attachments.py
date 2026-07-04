import frappe

ALLOWED_TARGET_DOCTYPES = {"Lead", "WIT Intake Review"}
MAX_LINKED_FILES = 25


def link_communication_files(communication_name: str, target_doctype: str, target_name: str) -> int:
	"""Attach files from a Communication to another WIT record.

	This creates additional File records that reference the same stored file URL,
	so the original Communication remains intact.
	"""
	if not communication_name or not target_doctype or not target_name:
		return 0
	if target_doctype not in ALLOWED_TARGET_DOCTYPES:
		frappe.throw("Invalid attachment target", frappe.PermissionError)

	files = frappe.get_all(
		"File",
		filters={"attached_to_doctype": "Communication", "attached_to_name": communication_name},
		fields=["name", "file_name", "file_url", "is_private", "folder"],
		limit=MAX_LINKED_FILES,
	)
	count = 0
	for source in files:
		if not _is_safe_file_url(source.file_url):
			continue
		if _already_linked(source.file_url, target_doctype, target_name):
			continue
		frappe.get_doc(
			{
				"doctype": "File",
				"file_name": source.file_name,
				"file_url": source.file_url,
				"is_private": 1 if source.is_private else 0,
				"folder": source.folder or "Home/Attachments",
				"attached_to_doctype": target_doctype,
				"attached_to_name": target_name,
			}
		).insert(ignore_permissions=True)
		count += 1
	return count


def _is_safe_file_url(file_url: str) -> bool:
	file_url = str(file_url or "").strip()
	if not file_url:
		return False
	if file_url.startswith(("http://", "https://", "//")):
		return False
	return file_url.startswith(("/private/files/", "/files/"))


def _already_linked(file_url: str, target_doctype: str, target_name: str) -> bool:
	return bool(
		frappe.db.exists(
			"File",
			{
				"file_url": file_url,
				"attached_to_doctype": target_doctype,
				"attached_to_name": target_name,
			},
		)
	)

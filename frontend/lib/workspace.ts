// Anonymous workspace: a UUID v4 kept in this browser and sent with every request (APP_FLOW §2).
const KEY = "coursemind.workspace";
const UUID_V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

let current: string | null = null;

export function getWorkspaceId(): string {
  if (current) return current;
  let id: string | null = null;
  try {
    id = localStorage.getItem(KEY);
  } catch {
    // Storage blocked (private mode, site data off): the id lives for this page load only.
  }
  if (!id || !UUID_V4.test(id)) {
    id = crypto.randomUUID();
    try {
      localStorage.setItem(KEY, id);
    } catch {}
  }
  current = id;
  return id;
}

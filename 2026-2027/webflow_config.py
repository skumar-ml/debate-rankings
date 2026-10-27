"""Replace one Webflow CMS collection with ranking rows.

Used by the PF and LD push scripts in this season folder. Talks to the
Webflow API directly. It does not import or call the Debate Land monorepo.

A push lists every item, unpublishes live items, deletes them, inserts the
new rows in batches of 100, then publishes those new items. A deleted item
can keep its slug after the collection is empty. When Webflow rejects that
slug, the rows not yet inserted are sent again with a new slug. The public
site can keep the previous HTML until that page is published in the Designer.
"""

import json
import re
import time
import unicodedata
import urllib.error
import urllib.request

API = "https://api.webflow.com/v2"
BATCH = 100


def item_slug(name, rank):
    base = unicodedata.normalize("NFKD", name)
    base = "".join(ch for ch in base if not unicodedata.combining(ch))
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:200]
    return f"{base or 'entry'}-{rank}"


def _request(token, method, path, body=None, retried=False):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        API + path,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Content-Type": "application/json",
            "accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            raw = res.read().decode()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as err:
        if err.code == 429 and not retried:
            wait = min(int(err.headers.get("Retry-After") or "60"), 70)
            time.sleep(wait)
            return _request(token, method, path, body, retried=True)
        detail = err.read().decode(errors="replace")[:500]
        raise RuntimeError(f"Webflow {err.code} on {path}: {detail}") from None


def _chunks(items, size):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _item_ids(payload):
    if not isinstance(payload, dict):
        return []
    ids = []
    if isinstance(payload.get("id"), str):
        ids.append(payload["id"])
    for item in payload.get("items") or []:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            ids.append(item["id"])
    return ids


def _list_items(token, collection_id):
    found = []
    offset = 0
    while True:
        page = _request(
            token,
            "GET",
            f"/collections/{collection_id}/items?limit={BATCH}&offset={offset}",
        )
        items = (page or {}).get("items") or []
        found.extend(items)
        offset += len(items)
        total = ((page or {}).get("pagination") or {}).get("total")
        if len(items) < BATCH or (total is not None and offset >= total):
            break
        if offset > 20000:
            break
    return found


def _log(message):
    print(message, flush=True)


def _delete_items(token, collection_id, path, ids, label=None):
    done = 0
    for batch in _chunks(ids, BATCH):
        _request(
            token,
            "DELETE",
            f"/collections/{collection_id}/items{path}",
            {"items": [{"id": item_id} for item_id in batch]},
        )
        done += len(batch)
        if label:
            _log(f"{label}: {done} of {len(ids)}")


def _is_live(item):
    return bool(item.get("lastPublished")) or item.get("isDraft") is False


def _avoid_reserved_slugs(rows):
    """Deleted items keep their slug after they disappear from the collection."""
    stamp = format(int(time.time() * 1000), "x")
    stamped = []
    for row in rows:
        slug = row.get("slug") or "entry"
        copied = dict(row)
        copied["slug"] = f"{slug}-{stamp}"[:256]
        stamped.append(copied)
    return stamped


def replace_collection(token, collection_id, items):
    """Delete every item in the collection, insert `items`, then publish.

    Each item is {"name", "slug", "fields"} where fields maps a Webflow field
    slug to a string or number.
    """
    _log("Listing existing Webflow items.")
    existing = _list_items(token, collection_id)
    remove = list(dict.fromkeys(item["id"] for item in existing if item.get("id")))
    live = list(dict.fromkeys(item["id"] for item in existing if item.get("id") and _is_live(item)))
    _log(f"Found {len(remove)} existing items.")
    if not remove and not live:
        _log("Collection is empty, skipping delete.")
    if live:
        _delete_items(token, collection_id, "/live", live)
    if remove:
        _log(f"Deleting {len(remove)} items.")
        _delete_items(token, collection_id, "", remove, "Deleted")

    creates = []
    seen = set()
    for item in items:
        if item["slug"] in seen:
            continue
        seen.add(item["slug"])
        field_data = {"name": item["name"], "slug": item["slug"]}
        field_data.update(item["fields"])
        creates.append(field_data)

    publish_ids = []
    try:
        rows = creates
        start = 0
        stamped = False
        _log(f"Inserting {len(rows)} rows.")
        while start < len(rows):
            batch = rows[start : start + BATCH]
            try:
                created = _request(
                    token,
                    "POST",
                    f"/collections/{collection_id}/items/insert",
                    {"items": [{"fieldData": field_data, "isDraft": False} for field_data in batch]},
                )
                publish_ids.extend(_item_ids(created))
                start += len(batch)
                _log(f"Inserted {start} of {len(rows)}.")
            except RuntimeError as err:
                if stamped or "Unique value is already in database" not in str(err):
                    raise
                _log("A deleted slug is still reserved. Retrying the remaining rows with a new slug.")
                rows = rows[:start] + _avoid_reserved_slugs(rows[start:])
                stamped = True
        _log(f"Publishing {len(publish_ids)} CMS items.")
        published = 0
        unique_ids = list(dict.fromkeys(publish_ids))
        for batch in _chunks(unique_ids, BATCH):
            _request(
                token,
                "POST",
                f"/collections/{collection_id}/items/publish",
                {"itemIds": batch},
            )
            published += len(batch)
            _log(f"Published {published} of {len(unique_ids)}.")
    except Exception as err:
        raise RuntimeError(
            f"Deleted {len(remove)} existing items, then failed while inserting the new rows. {err}"
        ) from None

    return {"created": len(creates), "removed": len(remove)}

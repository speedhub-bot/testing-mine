"""
inbox_scanner.py — Outlook Substrate API inbox keyword scanning.
Extracted from meow.py MicrosoftChecker.check_inbox().
"""
import re
from urllib.parse import urlparse, parse_qs

_SUBSTRATE_CLIENT_ID = '0000000048170EF2'
_SUBSTRATE_SCOPE = 'https://substrate.office.com/User-Internal.ReadWrite'
_SUBSTRATE_SCOPE_ALT = 'service::outlook.office.com::MBI_SSL'
_SUBSTRATE_REDIRECT = 'https://login.live.com/oauth20_desktop.srf'
_SEARCH_URL = 'https://outlook.live.com/search/api/v2/query?n=124&cv=tNZ1DVP5NhDwG%2FDUCelaIu.124'

def _get_substrate_token(session, config: dict) -> str | None:
    """Get a per-session substrate token (no global cache — each account needs its own)."""
    import time

    timeout = int(config.get('timeout', 15))

    for scope in (_SUBSTRATE_SCOPE, _SUBSTRATE_SCOPE_ALT):
        try:
            auth_url = (
                f'https://login.live.com/oauth20_authorize.srf'
                f'?client_id={_SUBSTRATE_CLIENT_ID}&response_type=token'
                f'&scope={scope}&redirect_uri={_SUBSTRATE_REDIRECT}&prompt=none'
            )
            r = session.get(auth_url, timeout=timeout)
            token = parse_qs(urlparse(r.url).fragment).get('access_token', [None])[0]
            if token:
                return token
        except Exception:
            continue

    # Try fetching MSPCID from Outlook session
    try:
        session.get('https://outlook.live.com/owa/', timeout=timeout)
    except Exception:
        pass

    return None


def _build_search_payload(keyword: str) -> dict:
    return {
        'Cvid': '7ef2720e-6e59-ee2b-a217-3a4f427ab0f7',
        'Scenario': {'Name': 'owa.react'},
        'TimeZone': 'Egypt Standard Time',
        'TextDecorations': 'Off',
        'EntityRequests': [{
            'EntityType': 'Conversation',
            'ContentSources': ['Exchange'],
            'Filter': {'Or': [
                {'Term': {'DistinguishedFolderName': 'msgfolderroot'}},
                {'Term': {'DistinguishedFolderName': 'DeletedItems'}},
            ]},
            'From': 0,
            'Query': {'QueryString': keyword},
            'RefiningQueries': None,
            'Size': 25,
            'Sort': [
                {'Field': 'Score', 'SortDirection': 'Desc', 'Count': 3},
                {'Field': 'Time', 'SortDirection': 'Desc'},
            ],
            'EnableTopResults': True,
            'TopResultsCount': 3,
        }],
        'AnswerEntityRequests': [{
            'Query': {'QueryString': keyword},
            'EntityTypes': ['Event', 'File'],
            'From': 0,
            'Size': 10,
            'EnableAsyncResolution': True,
        }],
        'QueryAlterationOptions': {
            'EnableSuggestion': True,
            'EnableAlteration': True,
            'SupportedRecourseDisplayTypes': [
                'Suggestion', 'NoResultModification',
                'NoResultFolderRefinerModification',
                'NoRequeryModification', 'Modification',
            ],
        },
        'LogicalId': '446c567a-02d9-b739-b9ca-616e0d45905c',
    }


def check_inbox(
    session,
    email: str,
    keywords: list,
    config: dict,
) -> list:
    """
    Search the account's Outlook inbox for each keyword via the Substrate API.
    Returns list of (keyword, match_count) tuples where match_count > 0.
    """
    if not config.get('cap_inbox_scan', False):
        return []

    if not keywords:
        return []

    token = _get_substrate_token(session, config)
    if not token:
        return []

    cid = session.cookies.get('MSPCID', email)
    headers = {
        'Authorization': f'Bearer {token}',
        'X-AnchorMailbox': f'CID:{cid}',
        'Content-Type': 'application/json',
        'User-Agent': 'Outlook-Android/2.0',
        'Accept': 'application/json',
        'Host': 'substrate.office.com',
    }

    results = []
    timeout = int(config.get('timeout', 15))

    for keyword in keywords:
        keyword = keyword.strip()
        if not keyword:
            continue
        try:
            payload = _build_search_payload(keyword)
            r = session.post(_SEARCH_URL, json=payload, headers=headers, timeout=timeout)
            if r.status_code != 200:
                continue
            data = r.json()
            total = 0
            for entity_set in data.get('EntitySets', []):
                for result_set in entity_set.get('ResultSets', []):
                    total += (
                        result_set.get('Total')
                        or result_set.get('ResultCount')
                        or len(result_set.get('Results', []))
                    )
            if total > 0:
                results.append((keyword, total))
        except Exception:
            continue

    return results

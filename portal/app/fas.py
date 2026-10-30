"""Protocole openNDS FAS niveau 4 : décodage, hachage, réponses à authmon.

Référence : docs/integration-opennds.md. Toutes les fonctions sont pures
(pas de base, pas de Flask) pour être testables sans rien démarrer.
"""
import base64
import binascii
import hashlib
import re
from urllib.parse import quote

# Séparateur des paires clé=valeur dans la chaîne décodée (QUERYSEPARATOR dans openNDS)
_SEPARATOR = ", "
# hid, rhid et gatewayhash ont tous le même format : une empreinte sha256 en hexadécimal minuscule.
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


class FasError(ValueError):
    """Paramètre fas absent, mal encodé ou incohérent."""


def is_sha256_hex(value: str) -> bool:
    """Vrai si `value` est une empreinte sha256 hexadécimale minuscule de 64 caractères."""
    return bool(_SHA256_HEX_RE.match(value))


def parse_fas(b64: str) -> dict[str, str]:
    """Décode le paramètre `fas` envoyé par openNDS en dictionnaire.

    La chaîne décodée est de la forme :
        hid=…, clientip=…, clientmac=…, gatewayname=…, …, resto=coeur-de-beurre
    Lève FasError si le base64 est invalide ou si `hid` n'est pas un sha256 hex.
    """
    if not b64:
        raise FasError("paramètre fas absent")
    try:
        decoded = base64.b64decode(b64, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise FasError("paramètre fas illisible") from exc

    params: dict[str, str] = {}
    for pair in decoded.split(_SEPARATOR):
        if "=" not in pair:
            continue
        key, value = pair.split("=", 1)
        params[key.strip()] = value.strip()

    hid = params.get("hid", "")
    if not is_sha256_hex(hid):
        raise FasError("hid absent ou invalide")
    return params


def compute_rhid(hid: str, fas_key: str) -> str:
    """Return hash id : sha256 de la concaténation hid + faskey, en hex minuscule.

    Source : openNDS client_list.c (`"%s%s", ptr->hid, config->fas_key`).
    """
    return hashlib.sha256((hid + fas_key).encode("utf-8")).hexdigest()


def gateway_hash(gatewayname_urlencoded: str) -> str:
    """Identifiant de la passerelle utilisé par authmon : sha256 du gatewayname URL-encodé.

    Source : openNDS main.c (hash_str sur config->url_encoded_gw_name).
    On hache la valeur telle que reçue dans `fas`, sans la décoder.
    """
    return hashlib.sha256(gatewayname_urlencoded.encode("utf-8")).hexdigest()


def build_auth_line(
    rhid: str,
    sessionlength: int = 240,
    uploadrate: int = 2000,
    downloadrate: int = 8000,
    uploadquota: int = 0,
    downloadquota: int = 0,
    custom: str = "",
) -> str:
    """Ligne d'autorisation lue par authmon puis passée à `ndsctl auth`.

    Unités : minutes, kbit/s, kbit/s, ko, ko. 0 = illimité.
    `custom` est encodé en base64 (transmis au script BinAuth du routeur).
    """
    custom_b64 = base64.b64encode(custom.encode("utf-8")).decode("ascii") if custom else ""
    return f"{rhid} {sessionlength} {uploadrate} {downloadrate} {uploadquota} {downloadquota} {custom_b64}".rstrip()


def encode_auth_list(lines: list[str]) -> str:
    """Réponse à `auth_get=view` ou `list` : `*` puis chaque ligne URL-encodée, séparées par des espaces.

    authmon lit le premier caractère (`*`), puis décode les `%20` en espaces.
    Équivalent du rawurlencode() PHP : tout est encodé sauf lettres, chiffres et -_.~
    """
    return "*" + "".join(" " + quote(line, safe="") for line in lines)


def decode_payload(payload_b64: str) -> str:
    """Décode le payload base64 envoyé par authmon. Renvoie "none" s'il est absent ou illisible."""
    if not payload_b64:
        return "none"
    try:
        return base64.b64decode(payload_b64, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return "none"


def parse_acklist(payload: str) -> set[str]:
    """Extrait les rhid acquittés par authmon d'un payload de la forme "* rhid1 rhid2".

    Seules les valeurs sha256 hexadécimales bien formées sont gardées, le reste est ignoré.
    """
    return {token for token in payload.split() if is_sha256_hex(token)}

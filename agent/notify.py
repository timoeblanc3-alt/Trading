"""Notifications sur le téléphone via ntfy (application gratuite, iOS et Android).

Le nom du « topic » sert de mot de passe : quiconque le connaît peut lire les messages.
Il est lu dans la variable NTFY_TOPIC ; sans elle, aucune notification n'est envoyée."""

import json
import os
import urllib.request

NTFY_URL = "https://ntfy.sh/"


def send(title, message, priority=3, tags=None):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return False
    body = {"topic": topic, "title": title, "message": message, "priority": priority, "tags": tags or []}
    req = urllib.request.Request(NTFY_URL, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15):
            return True
    except Exception as e:  # une notification ratée ne doit jamais bloquer le trading
        print(f"  (notification non envoyée : {e})")
        return False

"""Analyste IA (Claude) : relit chaque signal mécanique avec le contexte (actualité, macro,
positionnement) et peut le REFUSER. Il ne peut jamais créer un trade ni modifier taille ou stop :
ces décisions restent au code déterministe (stratégie + gestionnaire de risque).

Nécessite la variable d'environnement ANTHROPIC_API_KEY. Sans elle, l'analyste est désactivé
et le signal mécanique passe tel quel (le journal l'indique)."""

import json
import os
from dataclasses import dataclass

MODEL = "claude-opus-5-5"

SYSTEM = """Tu es l'analyste de risque d'un système de trading systématique sur les perpétuels Hyperliquid.
Une stratégie de suivi de tendance (cassure de Donchian, méthode des Turtles) a produit un signal.
Le dimensionnement, le stop et l'objectif sont déjà fixés par du code ; tu ne peux pas les changer.

Ton seul rôle : décider si le contexte actuel rend ce trade déraisonnable. Cherche sur le web :
- une annonce macro majeure dans les prochaines 24 h (FOMC, CPI, NFP) ;
- un événement propre à l'actif (hack, faille, délisting, procès, déblocage massif de tokens, ETF) ;
- un contexte qui contredit fortement le sens du trade.

Le suivi de tendance gagne grâce à quelques grosses tendances et perd souvent sur des faux départs :
un taux de réussite de 35 à 40 % est normal. Ne refuse donc PAS un trade pour un simple avis de marché,
une incertitude générale ou parce que « le prix est déjà monté ». Refuse seulement pour un risque
concret, daté et vérifiable, et cite ta source. En cas de doute sans fait précis : approuve.

N'invente aucun chiffre : les prix et indicateurs fournis viennent de l'API de l'exchange."""

SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {"type": "string", "enum": ["approve", "veto"]},
        "summary": {"type": "string", "description": "Deux à quatre phrases en français."},
        "risks": {"type": "array", "items": {"type": "string"}},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["decision", "summary", "risks", "sources"],
    "additionalProperties": False,
}


@dataclass
class Verdict:
    approved: bool
    summary: str
    risks: list
    sources: list
    available: bool = True


def available():
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _prompt(signal, context):
    return (
        f"Signal : {signal.side.upper()} {signal.coin}-USD perpétuel\n"
        f"Stratégie : {signal.strategy} ({signal.reason})\n"
        f"Entrée ≈ {signal.entry:.4f}, stop {signal.stop:.4f}, objectif {signal.target:.4f} "
        f"(ratio {signal.reward_risk:.1f})\n"
        f"Contexte de marché (API Hyperliquid) : {json.dumps(context, ensure_ascii=False)}\n\n"
        "Vérifie l'actualité pertinente puis rends ton verdict."
    )


def review(signal, context):
    if not available():
        return Verdict(True, "Analyste désactivé (pas de ANTHROPIC_API_KEY) : signal mécanique seul.",
                       [], [], available=False)
    import anthropic

    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": _prompt(signal, context)}]
    try:
        for _ in range(4):  # la recherche web peut interrompre le tour (pause_turn)
            response = client.beta.messages.create(
                model=MODEL,
                max_tokens=16000,
                system=SYSTEM,
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
                tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 5}],
                output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
                messages=messages,
            )
            if response.stop_reason != "pause_turn":
                break
            messages.append({"role": "assistant", "content": response.content})
    except anthropic.APIConnectionError:
        return Verdict(True, "Analyste injoignable (réseau) : signal mécanique seul.", [], [], available=False)
    except anthropic.RateLimitError:
        return Verdict(True, "Analyste limité en débit : signal mécanique seul.", [], [], available=False)
    except anthropic.APIStatusError as e:
        return Verdict(True, f"Erreur de l'analyste ({e.status_code}) : signal mécanique seul.", [], [],
                       available=False)

    if response.stop_reason == "refusal":
        return Verdict(True, "L'analyste a décliné la demande : signal mécanique seul.", [], [], available=False)
    text = next((b.text for b in reversed(response.content) if b.type == "text"), "")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return Verdict(True, "Réponse de l'analyste illisible : signal mécanique seul.", [], [], available=False)
    return Verdict(data["decision"] == "approve", data["summary"], data["risks"], data["sources"])

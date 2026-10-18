"""Indicateurs techniques en Python pur. Chaque fonction renvoie une liste alignée sur l'entrée
(None tant que la fenêtre n'est pas remplie)."""


def sma(values, n):
    out, total = [], 0.0
    for i, v in enumerate(values):
        total += v
        if i >= n:
            total -= values[i - n]
        out.append(total / n if i >= n - 1 else None)
    return out


def ema(values, n):
    out, prev, k = [], None, 2 / (n + 1)
    for i, v in enumerate(values):
        if i < n - 1:
            out.append(None)
            continue
        prev = sum(values[:n]) / n if prev is None else v * k + prev * (1 - k)
        out.append(prev)
    return out


def _wilder(values, n):
    """Lissage de Wilder ; `values` peut commencer par des None."""
    out, prev, buf = [], None, []
    for v in values:
        if v is None:
            out.append(None)
            continue
        if prev is None:
            buf.append(v)
            if len(buf) == n:
                prev = sum(buf) / n
            out.append(prev)
        else:
            prev = (prev * (n - 1) + v) / n
            out.append(prev)
    return out


def true_range(highs, lows, closes):
    tr = [highs[0] - lows[0]]
    for i in range(1, len(closes)):
        tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    return tr


def atr(highs, lows, closes, n=14):
    return _wilder(true_range(highs, lows, closes), n)


def rsi(closes, n=14):
    gains, losses = [None], [None]
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    ag, al = _wilder(gains, n), _wilder(losses, n)
    out = []
    for g, l in zip(ag, al):
        if g is None or l is None:
            out.append(None)
        elif l == 0:
            out.append(100.0)
        else:
            out.append(100 - 100 / (1 + g / l))
    return out


def adx(highs, lows, closes, n=14):
    plus_dm, minus_dm = [None], [None]
    for i in range(1, len(closes)):
        up, down = highs[i] - highs[i - 1], lows[i - 1] - lows[i]
        plus_dm.append(up if up > down and up > 0 else 0.0)
        minus_dm.append(down if down > up and down > 0 else 0.0)
    tr = [None] + true_range(highs, lows, closes)[1:]
    s_tr, s_p, s_m = _wilder(tr, n), _wilder(plus_dm, n), _wilder(minus_dm, n)
    dx = []
    for t, p, m in zip(s_tr, s_p, s_m):
        if t is None or p is None or m is None or t == 0:
            dx.append(None)
            continue
        pdi, mdi = 100 * p / t, 100 * m / t
        dx.append(0.0 if pdi + mdi == 0 else 100 * abs(pdi - mdi) / (pdi + mdi))
    return _wilder(dx, n)


def donchian(highs, lows, n):
    """Plus haut / plus bas des n bougies PRÉCÉDENTES (exclut la bougie courante)."""
    upper, lower = [], []
    for i in range(len(highs)):
        if i < n:
            upper.append(None)
            lower.append(None)
        else:
            upper.append(max(highs[i - n:i]))
            lower.append(min(lows[i - n:i]))
    return upper, lower

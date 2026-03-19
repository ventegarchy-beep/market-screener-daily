#!/usr/bin/env python3
"""
Stock Screener v3
S&P 500 | NASDAQ 100 | CAC 40 — Full Auto
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json, requests, time, logging, os, webbrowser
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
# Supprimer les messages parasites yfinance
logging.getLogger('yfinance').setLevel(logging.CRITICAL)
logging.getLogger('peewee').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)

# ================================================================
#  CONFIGURATION
# ================================================================
MARKETS        = ["CAC40", "DAX", "AEX", "IBEX", "FTSEMIB", "FTSE100", "NORDIC",
                  "SP500", "NASDAQ100", "US_GROWTH"]
TOP_N          = 15
DEEP_POOL      = 100   # Augmenté : on analyse plus de candidats pour ne rien rater
OUTPUT_FILE    = "daily_report.html"
SCAN_PERIOD    = "6mo" # Élargi à 6 mois pour capter les rebonds depuis creux
HISTORY_PERIOD = "6mo"
CHART_BARS     = 90

# ── Watchlist personnalisée ──────────────────────────────────────
WATCHLIST_FILE = "watchlist.txt"
WATCHLIST      = [
    "ALMDT.PA",   # Median Technologies
    "VU.PA",      # Vusion Group
    "AL2SI.PA",   # 2CRSi (ticker corrigé)
    "ALSEN.PA",   # Sensorion (ticker corrigé)
    "ALTHX.PA",   # Altheora / THX Pharma
    "DBV.PA",     # DBV Technologies
]
# ────────────────────────────────────────────────────────────────

# ── Filtres qualité ─────────────────────────────────────────────
MIN_POTENTIEL_PCT = 15.0
MIN_MARKET_CAP    = 2e6
MIN_AVG_VOLUME    = 1_000
MIN_PRICE         = 0.05
# ────────────────────────────────────────────────────────────────

WEIGHTS = {
    "technique":    0.30,
    "fondamentaux": 0.25,
    "finances":     0.20,
    "news":         0.15,
    "reseaux":      0.10,
}

# ================================================================
#  TRADUCTION SECTEURS EN/FR
# ================================================================
SECTOR_FR = {
    "Technology":               "Technologie",
    "Healthcare":               "Santé",
    "Financial Services":       "Services Financiers",
    "Consumer Cyclical":        "Conso. Cyclique",
    "Consumer Defensive":       "Conso. Défensive",
    "Industrials":              "Industrie",
    "Basic Materials":          "Matériaux",
    "Energy":                   "Energie",
    "Utilities":                "Services Publics",
    "Real Estate":              "Immobilier",
    "Communication Services":   "Communication",
    "Financial":                "Finance",
    "N/A":                      "N/A",
}

def fr_sector(s):
    return SECTOR_FR.get(s, s)

# ================================================================
#  UNIVERS — LISTES HARDCODÉES (pas de Wikipedia)
# ================================================================

CAC40_TICKERS = [
    "AI.PA","AIR.PA","ALO.PA","ACA.PA","BNP.PA","BN.PA","CAP.PA","CA.PA",
    "CS.PA","DSY.PA","EDEN.PA","EL.PA","ENGI.PA","ERF.PA","GLE.PA","HO.PA",
    "KER.PA","LR.PA","MC.PA","ML.PA","OR.PA","ORA.PA","PUB.PA","RI.PA",
    "RMS.PA","RNO.PA","SAF.PA","SAN.PA","SGO.PA","STM.PA","SU.PA","TEP.PA",
    "TTE.PA","URW.PA","VIE.PA","VIV.PA","DG.PA","WLN.PA","SW.PA","MT.AS",
]

# CAC All-Tradable + Small caps françaises notables
CAC_ALL_EXTRA = [
    # ── Mid caps françaises ─────────────────────────────────────
    "ALMDT.PA","VU.PA","DBV.PA","AURE.PA","SESG.PA",
    "SFCA.PA","MERY.PA","BOI.PA","ALLIX.PA","FNAC.PA",
    "ODET.PA","SQLI.PA","INFE.PA","LDL.PA","TKO.PA",
    "AURES.PA","NANO.PA","VIE.PA","LACR.PA","FLO.PA",
    # ── Small caps à potentiel — tickers Euronext vérifiés ──────
    "AL2SI.PA",  # 2CRSi — serveurs reconditionnés/recyclage IT (ticker corrigé)
    "ALSEN.PA",  # Sensorion — thérapeutique auditive
    "THX.PA",    # Thermador Groupe — distribution industrielle (≠ THX Pharma)
    "ALTHS.PA",  # Theranexus — biotech SNC
    "GENFIT.PA", # Genfit — biotech
    "ABCA.PA",   # ABC Arbitrage
    "ALWIT.PA",  # Witbe — monitoring réseaux
    "ALVDM.PA",  # Verimatrix — cybersécurité
    "MLGUI.PA",  # Guillemot — gaming peripherals
    "ALSGD.PA",  # Sword Group — ESN
    "ALCOF.PA",  # Coface
    "ALCLS.PA",  # Clasquin — logistique
    "MBWS.PA",   # Marie Brizard — boissons
    "ALTVO.PA",  # Teract — retail
    "ALPRS.PA",  # Parrot — drones
    "ALDLS.PA",  # Dalet — médias
    "ALPHY.PA",  # Phytocontrol — analyses
    "ALORB.PA",  # Orbis
    "MLBIO.PA",  # Biom'up
    "BIVI.PA",   # Biovelocita
    "ALCRB.PA",  # Carbon
    "ALMSB.PA",  # MSB Finance
    "HMY.PA",    # Harmony
    "CROS.PA",   # Crossject
    "MRM.PA",    # MRM
    # ── Biotech / Pharma françaises small cap ────────────────────
    "ALTHX.PA",  # Altheora (ex-THX Pharma) — thérapeutiques innovantes
    "ALDRX.PA",  # DrugStore Pharma
    "ALBIO.PA",  # Biocorp — drug delivery
    "ALPCV.PA",  # Pierre Chevalier Vigor (Pharnext)
    "ALINN.PA",  # Innate Pharma — immuno-oncologie
    "ABIO.PA",   # Adocia — formulation insuline
    "ALGLD.PA",  # Goldis — biotech
    "ALVB.PA",   # Valbiotis — nutraceutique
    "ALTHE.PA",  # Theradiag
    "BINV.PA",   # Biom'up
    "OSE.PA",    # OSE Immunotherapeutics
    "ONXEO.PA",  # Onxeo — oncologie
    "CBOT.PA",   # Carbios — biotech recyclage
    "SPEL.PA",   # Sanofi Epigenetics
    "ADVICENNE.PA", # Advicenne — maladies rares
    "OPT.PA",    # Opsion Pharmaco
    # ── IT / Tech françaises small cap ──────────────────────────
    "ALCIR.PA",  # Cibox Interactive
    "ALHEX.PA",  # Hexaom
    "ALFRE.PA",  # Freelance.com
    "ALMAP.PA",  # Amplitude Surgical
    "MLNQ.PA",   # NetQuinox
    "ENVEA.PA",  # Envea Global
    "ESKER.PA",  # Esker — SaaS
    "ALAGR.PA",  # Agripower
    "ALLOG.PA",  # Logistri
    "MLMCP.PA",  # MaCaPharma
]

# ── DAX 40 — Allemagne (.DE) ────────────────────────────────────
DAX_TICKERS = [
    "ADS.DE","AIR.DE","ALV.DE","BAS.DE","BAYN.DE","BMW.DE","BEI.DE",
    "CON.DE","1COV.DE","DB1.DE","DBK.DE","DHL.DE","DTE.DE",
    "EOAN.DE","FRE.DE","HEI.DE","HEN3.DE","IFX.DE",
    "LIN.DE","MBG.DE","MRK.DE","MTX.DE","MUV2.DE",
    "PAH3.DE","PUM.DE","RHM.DE","RWE.DE","SAP.DE","SIE.DE",
    "SY1.DE","VNA.DE","VOW3.DE","ZAL.DE","QIA.DE",
    "SHL.DE","ENR.DE","P911.DE",
]

# ── AEX / Pays-Bas (.AS) ────────────────────────────────────────
AEX_TICKERS = [
    "ASML.AS","INGA.AS","PHIA.AS","RDSA.AS","HEIA.AS","NN.AS","RAND.AS",
    "ABN.AS","AKZA.AS","DSM.AS","IMCD.AS","LIGHT.AS","PRX.AS","TKWY.AS",
    "UNA.AS","WKL.AS","ADYEN.AS","BESI.AS","FLOW.AS","GLPG.AS",
]

# ── IBEX 35 — Espagne (.MC) ─────────────────────────────────────
IBEX_TICKERS = [
    "IBE.MC","ITX.MC","SAN.MC","TEF.MC","BBVA.MC","REP.MC","ACS.MC",
    "ANA.MC","BKT.MC","CABK.MC","ELE.MC","ENG.MC",
    "FER.MC","GRF.MC","IAG.MC","MAP.MC","MEL.MC",
    "MTS.MC","NTGY.MC","RED.MC","ROVI.MC","SAB.MC",
    "SOLARIA.MC","VIS.MC","CLNX.MC","AENA.MC",
]

# ── FTSE MIB — Italie (.MI) ─────────────────────────────────────
MIB_TICKERS = [
    "ENI.MI","ENEL.MI","ISP.MI","UCG.MI","MB.MI",
    "G.MI","LDO.MI","BAMI.MI",
    "CNHI.MI","ERG.MI","HER.MI",
    "MONC.MI","NEXI.MI","SRG.MI","STM.MI",
    "TEN.MI","TRN.MI","RACE.MI","PRY.MI",
]

# ── FTSE 100 — Royaume-Uni (.L) — NON éligible PEA ─────────────
FTSE100_TICKERS = [
    "AAL.L","ABF.L","ADM.L","AHT.L","ANTO.L","AZN.L","BA.L","BARC.L",
    "BATS.L","BHP.L","BP.L","BT-A.L","CCL.L","CPG.L","CRH.L","DGE.L",
    "DLG.L","EVR.L","EXPN.L","FERG.L","FLTR.L","GLEN.L","GSK.L","HLMA.L",
    "HSBA.L","IAG.L","IHG.L","IMB.L","INF.L","ITRK.L","JD.L","KGF.L",
    "LAND.L","LGEN.L","LLOY.L","LSE.L","MNG.L","MRO.L","NWG.L","NXT.L",
    "OCDO.L","PHNX.L","PRU.L","PSH.L","PSN.L","PSON.L","RB.L","REL.L",
    "RIO.L","RKT.L","RR.L","RS1.L","SBRY.L","SDR.L","SGE.L","SHEL.L",
    "SKG.L","SMT.L","SN.L","SPX.L","SSE.L","STAN.L","SVT.L","TSCO.L",
    "ULVR.L","UTG.L","VOD.L","WPP.L","WTB.L",
]

# ── OMX Stockholm / Nordiques (.ST) — éligibles PEA ────────────
# Note: Yahoo Finance utilise le format sans tiret pour les classes d'actions
NORDIC_TICKERS = [
    "VOLV-B.ST","ERIC-B.ST","SWED-A.ST","SEB-A.ST","INVE-B.ST",
    "SAND.ST","EVO.ST","ALFA.ST","ASSA-B.ST",
    "BOL.ST","ESSITY-B.ST","HM-B.ST",
    "NDA-SE.ST","NIBE-B.ST","SINCH.ST","SKF-B.ST",
    "TEL2-B.ST","TELIA.ST","SSAB-A.ST",
    "ATCO-A.ST","KINV-B.ST",
]

SP500_TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","BRK-B","LLY","AVGO",
    "JPM","V","UNH","MA","XOM","PG","HD","COST","JNJ","MRK","ABBV","CVX",
    "PEP","KO","WMT","ADBE","CRM","CSCO","ACN","MCD","TMO","BAC","ABT",
    "NFLX","CMCSA","NEE","DIS","TXN","WFC","DHR","AMD","ORCL","QCOM","PM",
    "AMGN","INTU","RTX","HON","IBM","NKE","LOW","CAT","GE","SPGI","AXP",
    "BMY","MDT","UPS","GS","MS","BLK","SCHW","ISRG","SYK","VRTX","REGN",
    "ZTS","C","ADI","DE","AMAT","KLAC","MU","LRCX","SNPS","CDNS","MRVL",
    "NOW","PANW","CRWD","DDOG","ZS","FTNT","SNOW","PLTR","TTD","WDAY",
    "VEEV","HUBS","MDB","DOCU","BILL","COIN","SHOP","SPOT","ROKU","RBLX",
    "F","GM","DAL","UAL","AAL","ABNB","BKNG","MAR","HLT","MGM","DKNG",
    "NIO","XPEV","RIVN","LCID","PTON","HOOD","AFRM","SOFI","UPST","OPEN",
    "BMRN","MRNA","BIIB","ILMN","EXAS","ALNY","INCY","NBIX","SGEN","IONS",
    "ENPH","SEDG","FSLR","BE","PLUG","CHPT","BLNK","NEP","AEP","SO","DUK",
    "PLD","AMT","EQIX","CCI","SPG","O","AVB","EXR","VTR","WY","DRE","PSA",
    "JPM","WFC","BAC","GS","MS","C","BK","STT","USB","PNC","TFC","KEY",
    "CVS","MCK","ABC","CAH","HUM","CI","AET","MOH","CNC","WCG","HCA","THC",
    "LMT","NOC","RTX","GD","BA","HII","L3T","LDOS","SAIC","CACI","BAH",
    "MO","PM","BTI","RAI","LO","VGR","SWMAY","IMBBY","JAPAF","BATS",
    "CLX","CHD","SJM","CPB","GIS","K","MDLZ","OTIS","CARR","TT","LEN",
    "DHI","PHM","TOL","NVR","GRMN","HAS","MAT","HOG","PII","FOXF","BRC",
    "EMR","ETN","PH","ROP","FTV","AME","GNRC","XYL","GWW","MSC","FAST",
    "CMI","PCAR","ODFL","JBHT","UNP","CSX","NSC","KSU","CP","CN","WAB",
    "URI","HSY","MKC","SYY","USFD","PFGC","CHEF","HRL","TSN","JBS","WH",
    "SBUX","CMG","YUM","DPZ","DENN","JACK","WEN","MCD","QSR","RRGB",
    "LVS","WYNN","CZR","MGM","BYD","CHDN","PENN","VICI","GLPI","RHP",
]

NASDAQ100_TICKERS = [
    "AAPL","MSFT","NVDA","AMZN","META","GOOGL","GOOG","TSLA","AVGO","ADBE",
    "COST","CSCO","NFLX","AMD","QCOM","INTU","AMAT","ISRG","BKNG","MU",
    "LRCX","ADI","KLAC","PANW","SNPS","CDNS","MRVL","GILD","ADP","REGN",
    "VRTX","MDLZ","SBUX","ASML","ABNB","PYPL","MELI","CRWD","FTNT","DDOG",
    "ZS","TEAM","OKTA","SNOW","PLTR","RBLX","COIN","HOOD","AFRM","BMRN",
    "MRNA","BIIB","ILMN","EXAS","ALNY","INCY","NBIX","IONS","TTD","WDAY",
    "VEEV","HUBS","MDB","DOCU","BILL","GTLB","RIVN","NIO","XPEV","SHOP",
    "AZN","PDD","JD","BIDU","WBA","PCAR","ODFL","EXC","XEL","AEP","FANG",
    "CSGP","FAST","ROST","DLTR","EA","ATVI","TTWO","NTES","NETEASE","NICE",
    "HON","ON","MCHP","SWKS","QRVO","NXPI","TXN","INTC","SMCI","ARM",
]

# ── US Small/Mid Cap Growth — secteurs innovants ─────────────────
# Space, Quantum, AI, Biotech émergent, Fintech, EV next gen
US_GROWTH_TICKERS = [
    # Space & Defence next-gen
    "RKLB","SPCE","RDW","ASTS","LUNR","MNTS","ACHR","JOBY","LILM",
    # Quantum computing
    "RGTI","IONQ","QUBT","QMCO","IQM",
    # AI / semiconducteurs émergents
    "SOUN","BBAI","IREN","CIFR","HUT","MARA","RIOT","CLSK",
    # Biotech small cap à fort potentiel
    "RXRX","APLS","KYMR","MIRM","PRAX","ARQT","NUVL","RVMD",
    "AUPH","INVA","LEGN","TGTX","ROIV","PGNY","IOVA","FATE",
    # Fintech / Crypto émergent
    "MSTR","CLBT","UPST","DAVE","SOFI","CLOV","OPEN","HIMS",
    # EV / Clean energy next gen
    "NKLA","GOEV","WKHS","FFIE","IDEX","AYRO","SOLO","ZEV",
    # Divers high-growth
    "DUOL","AFRM","HOOD","GRAB","GRAB","SE","DKNG","PENN",
    "GENI","MGNI","PLTK","BMBL","MTCH","ANGI","YELP","WIX",
    "CELH","NOMD","VITL","PRPL","LAZY","LOVE","WOOF","GOED",
]

def get_universe(markets):
    tickers = []
    if "CAC40" in markets:
        tickers += CAC40_TICKERS
        tickers += CAC_ALL_EXTRA
    if "DAX" in markets:
        tickers += DAX_TICKERS
    if "AEX" in markets:
        tickers += AEX_TICKERS
    if "IBEX" in markets:
        tickers += IBEX_TICKERS
    if "FTSEMIB" in markets:
        tickers += MIB_TICKERS
    if "FTSE100" in markets:
        tickers += FTSE100_TICKERS
    if "NORDIC" in markets:
        tickers += NORDIC_TICKERS
    if "SP500" in markets:
        tickers += SP500_TICKERS
    if "NASDAQ100" in markets:
        tickers += NASDAQ100_TICKERS
    if "US_GROWTH" in markets:
        tickers += US_GROWTH_TICKERS

    # ── Watchlist personnalisée ──────────────────────────────────
    watchlist = list(WATCHLIST)  # depuis la config
    import os
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    t = line.strip().upper()
                    if t and not t.startswith("#"):
                        watchlist.append(t)
            if watchlist:
                print(f"  Watchlist : {len(watchlist)} tickers depuis {WATCHLIST_FILE}")
        except Exception as e:
            print(f"  Watchlist erreur : {e}")

    # Les tickers de la watchlist passent toujours en phase 2
    # (on les met en tête de liste)
    all_tickers = watchlist + [t for t in tickers if t not in set(watchlist)]

    seen, unique = set(), []
    for t in all_tickers:
        if t not in seen:
            seen.add(t); unique.append(t)
    print(f"  Univers total : {len(unique)} tickers"
          + (f" (dont {len(watchlist)} watchlist)" if watchlist else ""))
    return unique, set(watchlist)

# ================================================================
#  INDICATEURS TECHNIQUES
# ================================================================

def rsi(s, p=14):
    d = s.diff()
    g = d.clip(lower=0).rolling(p).mean()
    l = (-d.clip(upper=0)).rolling(p).mean()
    return 100 - 100 / (1 + g / l.replace(0, np.nan))

def macd(s, fast=12, slow=26, sig=9):
    ef = s.ewm(span=fast, adjust=False).mean()
    es = s.ewm(span=slow, adjust=False).mean()
    line = ef - es
    signal = line.ewm(span=sig, adjust=False).mean()
    return line, signal, line - signal

def ichimoku(high, low, close):
    ten = (high.rolling(9).max()  + low.rolling(9).min())  / 2
    kij = (high.rolling(26).max() + low.rolling(26).min()) / 2
    sa  = ((ten + kij) / 2).shift(26)
    sb  = ((high.rolling(52).max() + low.rolling(52).min()) / 2).shift(26)
    p, a, b = close.iloc[-1], sa.iloc[-1], sb.iloc[-1]
    if pd.isna(a) or pd.isna(b): return "Neutre"
    if p > max(a, b): return "Haussier"
    if p < min(a, b): return "Baissier"
    return "Neutre"

def atr(high, low, close, p=14):
    tr = pd.concat([high-low,(high-close.shift()).abs(),(low-close.shift()).abs()],axis=1).max(axis=1)
    return tr.rolling(p).mean()

def fibonacci(hi_s, lo_s):
    hi, lo = float(hi_s.max()), float(lo_s.min())
    r = hi - lo
    ret = {f"fib_{int(v*1000)}": round(hi - v*r, 4) for v in [0.236,0.382,0.500,0.618,0.786]}
    ext = {f"ext_{int(v*1000)}": round(lo + v*r, 4) for v in [1.000,1.272,1.618]}
    return {"high_ref":round(hi,4),"low_ref":round(lo,4),"retracements":ret,"extensions":ext}

# ================================================================
#  DÉTECTION DE FIGURES CHARTISTES
# ================================================================

def detect_patterns(cl: pd.Series, hi: pd.Series, lo: pd.Series, vol: pd.Series) -> list:
    """
    Détecte les figures chartistes haussières sur les données OHLCV.
    Retourne une liste de dicts {name, emoji, desc, strength (1-3)}.
    """
    patterns = []
    n = len(cl)
    if n < 50:
        return patterns

    prices = cl.values
    highs  = hi.values
    lows   = lo.values
    vols   = vol.values
    price  = prices[-1]

    # ── 1. DRAPEAU HAUSSIER ─────────────────────────────────────
    # Forte hausse (mât) suivie d'une consolidation serrée
    try:
        mat_start, mat_end = -35, -15
        flag_start         = -15

        mat_perf  = (prices[mat_end] / prices[mat_start] - 1) if prices[mat_start] > 0 else 0
        flag_high = float(np.max(prices[flag_start:]))
        flag_low  = float(np.min(prices[flag_start:]))
        flag_range = (flag_high - flag_low) / flag_low if flag_low > 0 else 1

        if mat_perf > 0.10 and flag_range < 0.07:
            strength = 3 if mat_perf > 0.20 else 2
            patterns.append({
                "name": "Drapeau Haussier",
                "emoji": "🚩",
                "desc": f"Mât +{mat_perf*100:.0f}% suivi d'une consolidation serrée ({flag_range*100:.1f}%)",
                "strength": strength,
            })
    except Exception:
        pass

    # ── 2. TASSE AVEC ANSE ──────────────────────────────────────
    # Forme en U sur ~40 séances + légère consolidation finale
    try:
        cup = prices[-60:-10] if n >= 60 else prices[:-10]
        if len(cup) < 20:
            raise ValueError
        cup_left  = float(np.mean(cup[:5]))
        cup_bottom= float(np.min(cup))
        cup_right = float(np.mean(cup[-5:]))
        handle    = prices[-10:]

        depth      = (cup_left - cup_bottom) / cup_left if cup_left > 0 else 0
        recovery   = (cup_right - cup_bottom) / (cup_left - cup_bottom) if (cup_left - cup_bottom) > 0 else 0
        handle_dip = (float(np.max(handle)) - float(np.min(handle))) / float(np.max(handle)) if float(np.max(handle)) > 0 else 1

        if 0.10 < depth < 0.40 and recovery > 0.75 and handle_dip < 0.07:
            strength = 3 if recovery > 0.90 and depth > 0.15 else 2
            patterns.append({
                "name": "Tasse avec Anse",
                "emoji": "🏆",
                "desc": f"Creux de {depth*100:.0f}%, récupération {recovery*100:.0f}%, anse serrée",
                "strength": strength,
            })
    except Exception:
        pass

    # ── 3. DOUBLE CREUX ─────────────────────────────────────────
    # Deux bas similaires séparés par un rebond, puis cassure
    try:
        w = min(n, 60)
        seg = lows[-w:]
        local_mins = []
        for i in range(2, len(seg)-2):
            if seg[i] <= seg[i-1] and seg[i] <= seg[i-2] and seg[i] <= seg[i+1] and seg[i] <= seg[i+2]:
                local_mins.append((i, seg[i]))

        if len(local_mins) >= 2:
            b1_idx, b1 = local_mins[-2]
            b2_idx, b2 = local_mins[-1]
            gap = b2_idx - b1_idx
            diff = abs(b1 - b2) / b1 if b1 > 0 else 1

            if gap >= 8 and diff < 0.04 and price > max(seg[b1_idx:b2_idx+1]) * 0.99:
                patterns.append({
                    "name": "Double Creux",
                    "emoji": "⬇️",
                    "desc": f"2 creux à {b1:.2f} / {b2:.2f} (écart {diff*100:.1f}%), cassure en cours",
                    "strength": 2,
                })
    except Exception:
        pass

    # ── 4. TRIANGLE ASCENDANT ───────────────────────────────────
    # Résistance horizontale + creux ascendants
    try:
        w = min(n, 40)
        rec_highs = highs[-w:]
        rec_lows  = lows[-w:]

        resistance = float(np.percentile(rec_highs, 90))
        touches_res = sum(1 for h in rec_highs if h > resistance * 0.99)

        # Vérifier que les creux montent
        lows_first_half = float(np.mean(rec_lows[:w//2]))
        lows_sec_half   = float(np.mean(rec_lows[w//2:]))
        rising_lows     = lows_sec_half > lows_first_half * 1.02

        # Convergence : range se réduit
        range_first = float(np.mean(rec_highs[:w//2] - rec_lows[:w//2]))
        range_last  = float(np.mean(rec_highs[w//2:] - rec_lows[w//2:]))
        narrowing   = range_last < range_first * 0.75

        if touches_res >= 3 and rising_lows and narrowing:
            patterns.append({
                "name": "Triangle Ascendant",
                "emoji": "📐",
                "desc": f"Résistance testée {touches_res}× à ~{resistance:.2f}, creux ascendants",
                "strength": 2,
            })
    except Exception:
        pass

    # ── 5. BREAKOUT DE RÉSISTANCE ───────────────────────────────
    # Prix franchit un plus haut de 20 séances avec volume fort
    try:
        high_20 = float(np.max(highs[-21:-1]))
        avg_vol  = float(np.mean(vols[-20:]))
        last_vol = float(vols[-1])
        vol_surge = last_vol > avg_vol * 1.4

        if price > high_20 * 1.005 and vol_surge:
            strength = 3 if price > high_20 * 1.02 and last_vol > avg_vol * 2 else 2
            patterns.append({
                "name": "Breakout Résistance",
                "emoji": "🚀",
                "desc": f"Cassure du plus haut 20j ({high_20:.2f}) avec volume x{last_vol/avg_vol:.1f}",
                "strength": strength,
            })
    except Exception:
        pass

    # ── 6. GOLDEN CROSS ─────────────────────────────────────────
    # EMA20 vient de croiser au-dessus de l'EMA50
    try:
        ema20_s = cl.ewm(span=20, adjust=False).mean().values
        ema50_s = cl.ewm(span=50, adjust=False).mean().values
        # Croisement dans les 5 dernières séances
        cross_detected = False
        for i in range(-5, 0):
            if ema20_s[i] > ema50_s[i] and ema20_s[i-1] <= ema50_s[i-1]:
                cross_detected = True
                break
        if cross_detected:
            patterns.append({
                "name": "Golden Cross",
                "emoji": "✨",
                "desc": "EMA20 vient de croiser au-dessus de l'EMA50 (signal haussier fort)",
                "strength": 3,
            })
    except Exception:
        pass

    # ── 7. REBOND SUR SUPPORT EMA ───────────────────────────────
    # Prix rebondit sur EMA50 avec volume
    try:
        ema50_val = float(cl.ewm(span=50, adjust=False).mean().iloc[-1])
        ema50_old = float(cl.ewm(span=50, adjust=False).mean().iloc[-5])
        near_ema50 = abs(price - ema50_val) / ema50_val < 0.025
        was_below  = float(cl.iloc[-3]) < ema50_old * 1.01
        now_above  = price > ema50_val

        if near_ema50 and was_below and now_above:
            patterns.append({
                "name": "Rebond EMA50",
                "emoji": "↗️",
                "desc": f"Rebond sur support EMA50 ({ema50_val:.2f}), momentum retrouvé",
                "strength": 2,
            })
    except Exception:
        pass

    # Trier par force décroissante
    patterns.sort(key=lambda x: x["strength"], reverse=True)
    return patterns[:4]  # max 4 figures

# ================================================================
#  SCAN RAPIDE — Phase 1
# ================================================================

def quick_scan(tickers, batch_size=80):
    print(f"{'─'*56}")
    print(f"  PHASE 1 — Scan rapide ({len(tickers)} tickers)")
    print(f"{'─'*56}")
    scores = {}
    batches = [tickers[i:i+batch_size] for i in range(0,len(tickers),batch_size)]
    for idx, batch in enumerate(batches):
        print(f"  Batch {idx+1}/{len(batches)}...", end="\r")
        try:
            raw = yf.download(batch, period=SCAN_PERIOD, auto_adjust=True,
                              progress=False, threads=True, timeout=30)
            if raw.empty: continue
            close_df = raw["Close"] if isinstance(raw.columns, pd.MultiIndex) else raw
            for t in batch:
                try:
                    s = close_df[t].dropna() if t in close_df.columns else None
                    if s is None or len(s) < 20: continue
                    price = float(s.iloc[-1])
                    if price < MIN_PRICE: continue

                    n = len(s)
                    r1m  = (price/float(s.iloc[-20])-1) if n>=20 else 0
                    r3m  = (price/float(s.iloc[-60])-1) if n>=60 else (price/float(s.iloc[0])-1)
                    r6m  = price/float(s.iloc[0])-1
                    rv   = float(rsi(s).iloc[-1])
                    e50  = float(s.ewm(span=50,adjust=False).mean().iloc[-1])
                    e20  = float(s.ewm(span=20,adjust=False).mean().iloc[-1])

                    # Filtre : exclure seulement les cas extrêmes
                    if np.isnan(rv): continue
                    if rv > 90 or rv < 8: continue      # RSI extrême
                    if r6m < -0.75: continue            # Chute > 75% sur 6 mois

                    sc = 0

                    # ── Momentum positif ────────────────────────
                    if r1m > 0.08:  sc += 3
                    elif r1m > 0.03: sc += 2
                    elif r1m > 0:    sc += 1

                    # ── RSI ─────────────────────────────────────
                    if 35 <= rv <= 65:   sc += 3
                    elif 65 < rv <= 78:  sc += 1
                    elif 20 <= rv < 35:  sc += 2  # survente → opportunité

                    # ── Position par rapport aux moyennes ────────
                    if price > e20 > e50: sc += 3   # alignement haussier
                    elif price > e20:     sc += 2
                    elif price > e50:     sc += 1

                    # ── Performance 3 mois ───────────────────────
                    if r3m > 0.20:   sc += 3
                    elif r3m > 0.08: sc += 2
                    elif r3m > 0:    sc += 1

                    # ── BONUS : rebond depuis creux 6 mois ───────
                    # Action qui a fortement baissé sur 6 mois
                    # mais remonte sur le dernier mois (recovery)
                    if r6m < -0.20 and r1m > 0.05:
                        sc += 3   # rebond de recovery = fort signal
                    elif r6m < -0.10 and r1m > 0.03:
                        sc += 2

                    # ── BONUS : RSI survente + rebond récent ─────
                    if rv < 35 and r1m > 0:
                        sc += 2  # survente avec début de retournement

                    scores[t] = sc

                except: pass
        except Exception as e:
            print(f"\n  Batch {idx+1} err: {e}")

    candidates = [t for t,_ in sorted(scores.items(),
                  key=lambda x: x[1], reverse=True)[:DEEP_POOL]]
    print(f"\n  Scan termine. {len(scores)} tickers scores.")
    print(f"  {len(candidates)} candidats retenus pour analyse profonde.\n")
    return candidates

# ================================================================
#  NEWS SENTIMENT
# ================================================================

BULL_KW = ["beat","surges","record","upgrade","strong","growth","profit","deal",
           "positive","raises","exceeds","breakthrough","approval","approved",
           "outperform","higher","rallies","buy","overweight","recovery",
           "hausse","croissance","benefice","accord","approuve","releve",
           "rebond","dividende"]

BEAR_KW = ["miss","decline","cut","downgrade","weak","loss","warning","below",
           "concern","risk","investigation","lawsuit","recall","fraud","layoffs",
           "disappoints","falls","tumbles","sell","underweight","slowdown",
           "baisse","perte","enquete","fraude","licenciements","deçoit",
           "avertissement","chute"]

# ── Cache traduction pour éviter les doublons ─────────────────
_TRANS_CACHE = {}

def translate_title(title: str) -> str:
    """Traduit un titre court EN→FR via MyMemory API (gratuit, sans clé)."""
    if not title or len(title) < 5: return title
    # Mots exclusivement français (jamais en anglais)
    fr_only = {"les","des","une","est","sont","pour","avec","sur","dans","par",
               "que","qui","cette","leur","leurs","mais","aussi","très","même"}
    words = set(title.lower().split())
    if len(words & fr_only) >= 1: return title
    if title in _TRANS_CACHE: return _TRANS_CACHE[title]
    try:
        r = requests.get(
            "https://api.mymemory.translated.net/get",
            params={"q": title[:400], "langpair": "en|fr"},
            timeout=5, headers={"User-Agent": "Mozilla/5.0"}
        )
        if r.status_code == 200:
            data = r.json()
            status = data.get("responseStatus", 200)
            if status == 429 or status == 403:
                _TRANS_CACHE[title] = title; return title
            translated = data.get("responseData", {}).get("translatedText", "")
            # Vérifier que c'est bien du français (pas un renvoi de l'original)
            if (translated and len(translated) > 5
                    and translated.lower().strip() != title.lower().strip()):
                _TRANS_CACHE[title] = translated
                return translated
    except Exception:
        pass
    _TRANS_CACHE[title] = title
    return title

def translate_long(text: str, max_chars: int = 350) -> str:
    """Traduit un texte long EN→FR en le découpant par phrases."""
    if not text or len(text) < 10: return text
    # Détection français rapide
    fr_only = {"les","des","une","est","sont","pour","avec","sur","dans","par","que","qui"}
    if len(set(text.lower().split()) & fr_only) >= 2: return text
    # Découper en morceaux sur les frontières de phrases
    sentences = text.replace("!",".").replace("?",".").split(". ")
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) < max_chars:
            current += s + ". "
        else:
            if current: chunks.append(current.strip())
            current = s + ". "
    if current: chunks.append(current.strip())
    # Traduire chaque chunk
    translated_parts = []
    for chunk in chunks[:4]:  # max 4 chunks = ~1400 chars
        translated_parts.append(translate_title(chunk))
        time.sleep(0.1)  # rate limit MyMemory
    return " ".join(translated_parts)

def score_news(tk):
    try:
        raw_news = tk.news or []
        # yfinance 1.x : news peut etre une liste de dicts avec differentes structures
        articles = []
        for a in raw_news[:8]:
            if isinstance(a, dict):
                # Nouveau format yfinance (content wrapper) ou ancien format direct
                content = a.get("content") or a
                title = (content.get("title") or a.get("title") or "")
                link  = (content.get("canonicalUrl",{}).get("url") if isinstance(content.get("canonicalUrl"),dict)
                         else content.get("url") or a.get("link") or "")
                pub   = (content.get("pubDate") or a.get("providerPublishTime") or "")
                articles.append({"title": title, "url": link, "pub": pub})

        if not articles:
            return 2, "Aucune news recente disponible", []

        bull, bear = 0, 0
        for a in articles:
            t = a["title"].lower()
            b = sum(1 for w in BULL_KW if w in t)
            n = sum(1 for w in BEAR_KW if w in t)
            if b > n: bull += 1
            elif n > b: bear += 1

        total = len(articles)
        ratio = bull / total if total else 0.5

        news_items = []
        for a in articles[:3]:
            pub = a["pub"]
            if isinstance(pub, (int, float)) and pub > 0:
                date_s = datetime.fromtimestamp(pub).strftime("%d/%m/%Y")
            elif isinstance(pub, str) and pub:
                date_s = pub[:10]
            else:
                date_s = ""
            title_fr = translate_title(a["title"])
            news_items.append({"title": title_fr, "title_orig": a["title"],
                                "url": a["url"], "date": date_s})

        if   ratio > 0.70: stars, label = 4, f"Tres positif — {bull}/{total} bullish"
        elif ratio > 0.55: stars, label = 3, f"Positif — {bull}/{total} bullish"
        elif ratio > 0.40: stars, label = 2, f"Neutre — {bull}/{total} pos. / {bear}/{total} neg."
        else:              stars, label = 1, f"Negatif — {bear}/{total} bearish"
        return int(stars), label, news_items
    except Exception as e:
        return 2, f"News indisponibles ({e})", []

# ================================================================
#  SOCIAL SENTIMENT — StockTwits
# ================================================================

def score_social(symbol):
    try:
        clean = symbol.split(".")[0].replace("-","_").upper()
        url = f"https://api.stocktwits.com/api/2/streams/symbol/{clean}.json"
        r   = requests.get(url, timeout=8, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code == 429: return 2, "StockTwits : rate limit"
        if r.status_code != 200: return 2, f"StockTwits indisponible ({r.status_code})"
        msgs = r.json().get("messages", [])
        if not msgs: return 2, "Aucun message recent"
        bull = sum(1 for m in msgs if m.get("entities",{}).get("sentiment",{}).get("basic")=="Bullish")
        bear = sum(1 for m in msgs if m.get("entities",{}).get("sentiment",{}).get("basic")=="Bearish")
        tagged = bull + bear
        if tagged == 0: return 2, f"{len(msgs)} messages, aucun tagge"
        ratio = bull / tagged
        if   ratio > 0.75: return 4, f"Tres Bullish ({int(ratio*100)}%, {tagged} votes)"
        elif ratio > 0.60: return 3, f"Bullish ({int(ratio*100)}%, {tagged} votes)"
        elif ratio > 0.45: return 2, f"Neutre ({int(ratio*100)}%, {tagged} votes)"
        else:              return 1, f"Bearish ({int(ratio*100)}%, {tagged} votes)"
    except: return 2, "StockTwits indisponible"

# ================================================================
#  SCORING DÉTAILLÉ
# ================================================================

def score_technique(rsi_v, macd_h, ichi, price, ema20, ema50, vol_ratio,
                    momentum_5j=0.0, vol_surge_5j=False):
    score, d = 0.0, []
    if   40 <= rsi_v <= 60:  score+=1.0; d.append(f"RSI sain ({rsi_v:.0f})")
    elif 30 <= rsi_v < 40:   score+=0.75;d.append(f"RSI bas ({rsi_v:.0f}), rebond potentiel")
    elif rsi_v < 30:         score+=0.5; d.append(f"RSI survente ({rsi_v:.0f})")
    elif 60 < rsi_v <= 70:   score+=0.5; d.append(f"RSI eleve ({rsi_v:.0f})")
    if macd_h > 0:           score+=1.0; d.append("MACD haussier")
    else:                               d.append("MACD baissier")
    if ichi == "Haussier":   score+=1.0; d.append("Au-dessus nuage Ichimoku")
    elif ichi == "Neutre":   score+=0.5; d.append("Dans le nuage Ichimoku")
    else:                               d.append("Sous le nuage Ichimoku")
    if price > ema20 > ema50:score+=0.75;d.append("Alignement EMA haussier")
    elif price > ema20:      score+=0.5; d.append("Prix > EMA20")
    elif price > ema50:      score+=0.25;d.append("Prix > EMA50")
    if vol_ratio > 2.0:      score+=0.25;d.append(f"Volume x{vol_ratio:.1f}")
    # ── Momentum court terme (5 jours) ──────────────────────────
    if momentum_5j > 0.05:   score+=0.5; d.append(f"Momentum 5j +{momentum_5j*100:.1f}%")
    elif momentum_5j > 0.02: score+=0.25;d.append(f"Momentum 5j +{momentum_5j*100:.1f}%")
    elif momentum_5j < -0.05:score-=0.25;d.append(f"Momentum 5j {momentum_5j*100:.1f}%")
    # ── Alerte volume anormal ────────────────────────────────────
    if vol_surge_5j:
        score+=0.25; d.append("Volume x2 sur 5j (flux acheteur)")
    score = max(0, score)
    stars = max(0, min(4, int(round(score))))
    return stars, " | ".join(d) or "Signaux mixtes"

def score_fondamentaux(info):
    score, d = 0.0, []
    rev = info.get("revenueGrowth")
    if rev:
        if   rev>0.20: score+=1.0;d.append(f"Croissance CA +{rev*100:.0f}%")
        elif rev>0.08: score+=0.75;d.append(f"Croissance CA +{rev*100:.0f}%")
        elif rev>0:    score+=0.5; d.append(f"Croissance CA +{rev*100:.0f}%")
        else:                      d.append(f"CA en recul {rev*100:.0f}%")
    gm = info.get("grossMargins")
    if gm:
        if   gm>0.55: score+=1.0;d.append(f"Marge brute {gm*100:.0f}%")
        elif gm>0.35: score+=0.75;d.append(f"Marge brute {gm*100:.0f}%")
        elif gm>0.15: score+=0.5; d.append(f"Marge brute {gm*100:.0f}%")
    rec = info.get("recommendationMean", 3.5)
    if   rec<=1.5: score+=1.0;d.append("Strong Buy (consensus)")
    elif rec<=2.0: score+=0.75;d.append("Buy (consensus)")
    elif rec<=2.5: score+=0.5; d.append("Outperform (consensus)")
    elif rec<=3.0: score+=0.25;d.append("Hold (consensus)")
    else:                      d.append("Sell/Underperform")
    tgt = info.get("targetMeanPrice"); cur = info.get("currentPrice") or info.get("regularMarketPrice")
    if tgt and cur and float(cur)>0:
        up = float(tgt)/float(cur)-1
        if   up>0.40: score+=1.0;d.append(f"TP analystes +{up*100:.0f}%")
        elif up>0.20: score+=0.75;d.append(f"TP analystes +{up*100:.0f}%")
        elif up>0.10: score+=0.5; d.append(f"TP analystes +{up*100:.0f}%")
    stars = max(0, min(4, int(round(max(0, score)))))
    return stars, " | ".join(d) or "Donnees fondamentales limitees"

def score_finances(info):
    score, d = 0.0, []
    roe = info.get("returnOnEquity")
    if roe is not None:
        if   roe>0.25: score+=1.0;d.append(f"ROE {roe*100:.0f}%")
        elif roe>0.12: score+=0.75;d.append(f"ROE {roe*100:.0f}%")
        elif roe>0:    score+=0.5; d.append(f"ROE positif {roe*100:.0f}%")
        else:                      d.append(f"ROE negatif")
    pm = info.get("profitMargins")
    if pm is not None:
        if   pm>0.20: score+=1.0;d.append(f"Marge nette {pm*100:.0f}%")
        elif pm>0.08: score+=0.75;d.append(f"Marge nette {pm*100:.0f}%")
        elif pm>0:    score+=0.5; d.append(f"Marge nette {pm*100:.0f}%")
        else:                     d.append("Perte nette")
    dte = info.get("debtToEquity")
    if dte is not None:
        if   dte<30:  score+=1.0;d.append(f"Faible endettement (D/E={dte:.0f}%)")
        elif dte<80:  score+=0.75;d.append(f"Endettement modere (D/E={dte:.0f}%)")
        elif dte<150: score+=0.5; d.append(f"Endettement eleve (D/E={dte:.0f}%)")
        else:                     d.append(f"Tres endette (D/E={dte:.0f}%)")
    cr = info.get("currentRatio")
    if cr is not None:
        if   cr>2.5: score+=1.0;d.append(f"Liquidite forte (CR={cr:.1f})")
        elif cr>1.5: score+=0.75;d.append(f"Liquidite solide (CR={cr:.1f})")
        elif cr>1.0: score+=0.5; d.append(f"Liquidite correcte (CR={cr:.1f})")
        else:                    d.append(f"Liquidite fragile (CR={cr:.1f})")
    stars = max(0, min(4, int(round(max(0, score)))))
    return stars, " | ".join(d) or "Donnees financieres limitees"

# ================================================================
#  ANALYSE PROFONDE — Phase 2
# ================================================================

def analyze(symbol, force_include=False):
    try:
        tk   = yf.Ticker(symbol)
        hist = tk.history(period=HISTORY_PERIOD)
        info = tk.info or {}
        if hist.empty or len(hist) < 10:
            return None, "données insuffisantes"

        cl, hi, lo, vol = hist["Close"], hist["High"], hist["Low"], hist["Volume"]
        price   = float(cl.iloc[-1])
        var_pct = (price - float(cl.iloc[-2])) / float(cl.iloc[-2]) * 100

        # ── Filtres qualité (bypassés pour la watchlist) ─────────
        if not force_include:
            if price < MIN_PRICE:
                return None, f"prix trop bas ({price:.3f})"
            avg_vol_check = float(vol.rolling(20).mean().iloc[-1])
            if avg_vol_check < MIN_AVG_VOLUME:
                return None, "volume insuffisant"
            mkt_cap = info.get("marketCap") or 0
            if mkt_cap > 0 and mkt_cap < MIN_MARKET_CAP:
                return None, "capi trop faible"
        # ────────────────────────────────────────────────────────

        rsi_v    = float(rsi(cl).iloc[-1])
        _, _, mh = macd(cl)
        macd_h   = float(mh.iloc[-1])
        ema20    = float(cl.ewm(span=20,adjust=False).mean().iloc[-1])
        ema50    = float(cl.ewm(span=50,adjust=False).mean().iloc[-1])
        ichi_t   = ichimoku(hi, lo, cl)
        atr_v    = float(atr(hi, lo, cl).iloc[-1])
        avg_vol  = float(vol.rolling(20).mean().iloc[-1])
        vol_r    = float(vol.iloc[-1])/avg_vol if avg_vol>0 else 1.0
        # ── Momentum 5j et alerte volume ────────────────────────
        momentum_5j  = (float(cl.iloc[-1])/float(cl.iloc[-6])-1) if len(cl)>=6 else 0.0
        avg_vol_5j   = float(vol.iloc[-5:].mean()) if len(vol)>=5 else avg_vol
        vol_surge_5j = avg_vol > 0 and avg_vol_5j > avg_vol * 2.0
        # ────────────────────────────────────────────────────────
        fib      = fibonacci(hi, lo)
        poc      = round(float(cl.rolling(20).mean().iloc[-1]),2)

        stop = round(price - 2*atr_v, 2)

        # ── Sources de Take Profit enrichies ────────────────────
        tgt_mean = info.get("targetMeanPrice")
        tgt_high = info.get("targetHighPrice")
        high_52w = float(hi.max())  # Plus haut 52 semaines (sur HISTORY_PERIOD)
        fib_1272 = fib["extensions"]["ext_1272"]
        fib_1618 = fib["extensions"]["ext_1618"]
        fib_2618 = round(float(lo.min()) + 2.618 * (float(hi.max()) - float(lo.min())), 2)

        # Résistance 52W comme objectif si franchissement proche
        res_52w = round(high_52w * 1.03, 2)  # 3% au-dessus du plus haut

        # Sélection du TP le plus pertinent
        tp_candidates = []
        if tgt_mean and float(tgt_mean) > price * 1.05:
            tp_candidates.append((round(float(tgt_mean),2), "Analystes (12 mois)", 0))
        if tgt_high and float(tgt_high) > price * 1.15:
            tp_candidates.append((round(float(tgt_high),2), "Objectif haut analystes", 1))
        if fib_1272 > price * 1.05:
            tp_candidates.append((round(fib_1272,2), "Fibonacci 127.2%", 2))
        if fib_1618 > price * 1.05:
            tp_candidates.append((round(fib_1618,2), "Fibonacci 161.8%", 3))
        if fib_2618 > price * 1.10:
            tp_candidates.append((round(fib_2618,2), "Fibonacci 261.8%", 4))
        if res_52w > price * 1.05:
            tp_candidates.append((res_52w, "Résistance 52 semaines", 5))

        if tp_candidates:
            # Prendre le 2ème meilleur TP (évite les objectifs trop optimistes)
            tp_candidates.sort(key=lambda x: x[0])
            idx = min(1, len(tp_candidates)-1)
            tp, tp_src, _ = tp_candidates[idx]
        else:
            tp, tp_src = round(fib_1272, 2), "Fibonacci 127.2%"

        # Tous les TP disponibles pour affichage
        tp_all = [{"val": v, "src": s} for v, s, _ in sorted(tp_candidates, key=lambda x: x[0])]

        # ── Consensus analystes avec date réelle ────────────────
        rec      = info.get("recommendationMean", 3.0)
        nb_anal  = info.get("numberOfAnalystOpinions") or 0
        r6m_perf = (price / float(cl.iloc[0]) - 1) if len(cl) > 0 else 0

        if   rec<=1.5: consensus_lbl = "Strong Buy"
        elif rec<=2.5: consensus_lbl = "Buy"
        elif rec<=3.5: consensus_lbl = "Hold"
        else:          consensus_lbl = "Sell"

        # Récupérer la date réelle de la dernière recommandation
        last_reco_date = ""
        last_reco_age_days = None
        consensus_warn = ""
        try:
            upgrades = tk.upgrades_downgrades
            if upgrades is not None and not upgrades.empty:
                # Trier par date décroissante
                upgrades = upgrades.sort_index(ascending=False)
                last_date = upgrades.index[0]
                if hasattr(last_date, 'date'):
                    last_date = last_date.date()
                last_reco_date = last_date.strftime("%d/%m/%Y") if hasattr(last_date, 'strftime') else str(last_date)
                last_reco_age_days = (datetime.now().date() - last_date).days if hasattr(last_date, 'year') else None
        except Exception:
            pass

        # Construire l'alerte staleness avec info de date réelle
        age_txt = ""
        if last_reco_age_days is not None:
            if last_reco_age_days < 30:
                age_txt = f"dernière mise à jour il y a {last_reco_age_days}j ✅"
            elif last_reco_age_days < 90:
                age_txt = f"dernière mise à jour il y a {last_reco_age_days}j"
            else:
                age_txt = f"⚠️ dernière mise à jour il y a {last_reco_age_days}j — peut être obsolète"

        if r6m_perf < -0.25 and rec <= 2.5:
            consensus_warn = (
                f"⚠️ Consensus {consensus_lbl} à vérifier — "
                f"chute de {r6m_perf*100:.0f}% sur 6 mois"
                + (f" | {age_txt}" if age_txt else "")
                + f" | {nb_anal} analyste{'s' if nb_anal>1 else ''}"
            )
        elif r6m_perf > 0.50 and rec >= 3.0:
            consensus_warn = (
                f"⚠️ Consensus {consensus_lbl} potentiellement dépassé — "
                f"hausse +{r6m_perf*100:.0f}% sur 6 mois"
                + (f" | {age_txt}" if age_txt else "")
            )
        elif age_txt and last_reco_age_days and last_reco_age_days > 90:
            consensus_warn = f"{age_txt} | {nb_anal} analyste{'s' if nb_anal>1 else ''}"

        consensus = consensus_lbl

        rsi_sig = "🔴 Survente (rebond)" if rsi_v<30 else "🟡 Surachat" if rsi_v>70 else "🟢 Zone saine"

        t_s,   t_e   = score_technique(rsi_v, macd_h, ichi_t, price, ema20, ema50, vol_r,
                                        momentum_5j=momentum_5j, vol_surge_5j=vol_surge_5j)
        f_s,   f_e   = score_fondamentaux(info)
        fin_s, fin_e = score_finances(info)
        n_s, n_e, news_items = score_news(tk)
        time.sleep(0.25)
        soc_s, soc_e = score_social(symbol)

        # Forcer des entiers propres
        t_s, f_s, fin_s, n_s, soc_s = int(t_s), int(f_s), int(fin_s), int(n_s), int(soc_s)

        weighted = round(t_s*WEIGHTS["technique"] + f_s*WEIGHTS["fondamentaux"] +
                         fin_s*WEIGHTS["finances"] + n_s*WEIGHTS["news"] + soc_s*WEIGHTS["reseaux"], 2)
        stars    = max(1, min(4, int(round(weighted))))

        potentiel_pct = (tp - price) / price * 100 if price > 0 else 0

        # ── Filtre potentiel minimum (bypassé pour la watchlist) ─
        if not force_include and potentiel_pct < MIN_POTENTIEL_PCT:
            return None, f"potentiel faible ({potentiel_pct:.0f}%)"
        # ────────────────────────────────────────────────────────

        global_score  = round(
            weighted * min(potentiel_pct, 150) / 10,  # Potentiel plafonné à 150% dans le calcul
            2
        )

        curr = "EUR" if any(symbol.endswith(x) for x in [".PA",".DE",".AS",".MI",".MC",
                                                           ".BR",".LS",".VI"]) else \
               "GBP" if symbol.endswith(".L") else \
               "SEK" if symbol.endswith(".ST") else \
               "NOK" if symbol.endswith(".OL") else \
               "DKK" if symbol.endswith(".CO") else \
               "CHF" if symbol.endswith(".SW") else "USD"
        curr_sym = {"EUR":"€","GBP":"£","USD":"$","SEK":"kr","NOK":"kr",
                    "DKK":"kr","CHF":"CHF"}.get(curr, "$")

        # ── Drapeau pays + éligibilité PEA ──────────────────────
        # Règle PEA : société dont le siège social est dans l'UE ou l'EEE
        SUFFIX_INFO = {
            ".PA": ("🇫🇷", True,  "France"),
            ".DE": ("🇩🇪", True,  "Allemagne"),
            ".AS": ("🇳🇱", True,  "Pays-Bas"),
            ".MC": ("🇪🇸", True,  "Espagne"),
            ".MI": ("🇮🇹", True,  "Italie"),
            ".BR": ("🇧🇪", True,  "Belgique"),
            ".LS": ("🇵🇹", True,  "Portugal"),
            ".VI": ("🇦🇹", True,  "Autriche"),
            ".HE": ("🇫🇮", True,  "Finlande"),
            ".CO": ("🇩🇰", True,  "Danemark"),
            ".ST": ("🇸🇪", True,  "Suède"),     # EEE
            ".OL": ("🇳🇴", True,  "Norvège"),   # EEE
            ".SW": ("🇨🇭", False, "Suisse"),    # hors UE/EEE → non PEA
            ".L":  ("🇬🇧", False, "Royaume-Uni"),  # Brexit → non PEA
            ".IR": ("🇮🇪", True,  "Irlande"),
            ".AT": ("🇦🇹", True,  "Autriche"),
            ".WA": ("🇵🇱", True,  "Pologne"),
        }
        country_flag, is_pea, country_name = "🇺🇸", False, "États-Unis"
        for sfx, (flag, pea, cname) in SUFFIX_INFO.items():
            if symbol.endswith(sfx):
                country_flag, is_pea, country_name = flag, pea, cname
                break

        sector_en = info.get("sector", "N/A")
        sector    = fr_sector(sector_en)

        blocs = []
        if ichi_t=="Haussier":   blocs.append("Structure haussière au-dessus du nuage Ichimoku.")
        elif ichi_t=="Baissier": blocs.append("Pression vendeuse sous le nuage Ichimoku.")
        if macd_h>0:  blocs.append("MACD positif, momentum favorable.")
        if rsi_v<35:  blocs.append(f"RSI survente ({rsi_v:.0f}), rebond potentiel.")
        elif rsi_v>65:blocs.append(f"RSI élevé ({rsi_v:.0f}), surveiller excès.")
        if price>ema20>ema50: blocs.append("Alignement EMA20/EMA50 haussier.")
        tech_desc = " ".join(blocs) or "Signaux techniques mixtes, attendre confirmation."

        # ── Figures chartistes ───────────────────────────────────
        patterns = detect_patterns(cl, hi, lo, vol)

        chart_df     = hist.tail(CHART_BARS)
        chart_labels = [d.strftime("%d/%m") for d in chart_df.index]
        chart_prices = [round(float(v),4) for v in chart_df["Close"]]

        # ── Description société ──────────────────────────────────
        long_desc = info.get("longBusinessSummary") or ""
        # Tronquer à ~400 caractères sur une frontière de phrase
        if len(long_desc) > 420:
            cut = long_desc.rfind(". ", 0, 420)
            long_desc = long_desc[:cut+1] if cut > 100 else long_desc[:420] + "…"
        # Traduction FR si description en anglais
        about_text = translate_long(long_desc) if long_desc else ""

        # ── Insider trading (transactions dirigeants) ────────────
        insider_data = []
        try:
            insiders = tk.insider_transactions
            if insiders is not None and not insiders.empty:
                # Colonnes dispo selon version yfinance
                cols = insiders.columns.tolist()
                for _, row in insiders.head(8).iterrows():
                    try:
                        # Date
                        tx_date = ""
                        for dc in ["Start Date","startDate","Date","date"]:
                            if dc in cols and row.get(dc) is not None:
                                raw = row[dc]
                                if hasattr(raw,'strftime'): tx_date = raw.strftime("%d/%m/%Y")
                                else: tx_date = str(raw)[:10]
                                break

                        # Nom de l'insider
                        name_in = ""
                        for nc in ["Insider","insider","Name","name"]:
                            if nc in cols and row.get(nc):
                                name_in = str(row[nc]); break

                        # Type transaction
                        tx_type = ""
                        for tc in ["Transaction","transaction","Type","type"]:
                            if tc in cols and row.get(tc):
                                tx_type = str(row[tc]); break

                        # Nombre de titres
                        shares = 0
                        for sc in ["Shares","shares","Value","value"]:
                            if sc in cols and row.get(sc) is not None:
                                try: shares = int(float(row[sc])); break
                                except: pass

                        # Valeur €/$
                        value = 0
                        for vc in ["Value","value","Amount","amount"]:
                            if vc in cols and row.get(vc) is not None:
                                try: value = float(row[vc]); break
                                except: pass

                        if name_in or tx_type:
                            # Classer achat vs vente
                            tx_lower = tx_type.lower()
                            is_buy = any(w in tx_lower for w in
                                        ["purchase","buy","acquisition","achat","acqui"])
                            is_sell= any(w in tx_lower for w in
                                        ["sale","sell","sold","vente","cession","dispose"])
                            insider_data.append({
                                "date":    tx_date,
                                "name":    name_in,
                                "type":    tx_type,
                                "shares":  shares,
                                "value":   round(value, 0),
                                "is_buy":  is_buy,
                                "is_sell": is_sell,
                            })
                    except Exception:
                        continue
        except Exception:
            pass

        # ── Calendrier des événements à venir ────────────────────
        events = []
        try:
            cal = tk.calendar
            if cal is not None:
                def fmt_date(v):
                    if v is None: return ""
                    if hasattr(v, "strftime"): return v.strftime("%d/%m/%Y")
                    try: return str(v)[:10]
                    except: return ""

                # Résultats / publication CA
                for key, label, emoji in [
                    ("Earnings Date",       "Publication résultats",    "📊"),
                    ("Ex-Dividend Date",    "Détachement dividende",     "💰"),
                    ("Dividend Date",       "Paiement dividende",        "💰"),
                ]:
                    val = cal.get(key)
                    if val is not None:
                        # Peut être une liste ou une valeur simple
                        dates = val if isinstance(val, list) else [val]
                        for d_val in dates[:2]:
                            d_str = fmt_date(d_val)
                            if d_str:
                                events.append({"emoji": emoji, "label": label, "date": d_str})

                # Chiffre d'affaires estimé prochain trimestre
                rev_est = info.get("revenueEstimate") or info.get("revenueForCurrentYear")
                if rev_est:
                    events.append({"emoji": "📈", "label": "CA estimé prochain exercice",
                                   "date": f"{rev_est/1e6:.0f} M {curr_sym}"})

            # Essayer aussi earningsTimestamps
            try:
                ed = info.get("earningsTimestamps") or []
                for ts in ed[:2]:
                    if isinstance(ts, (int, float)) and ts > 0:
                        from datetime import datetime as _dt
                        d_str = _dt.fromtimestamp(ts).strftime("%d/%m/%Y")
                        if not any(e.get("date") == d_str for e in events):
                            events.append({"emoji": "📊", "label": "Publication résultats", "date": d_str})
            except Exception:
                pass
        except Exception:
            pass

        return {
            "ticker":          symbol,
            "name":            info.get("longName") or info.get("shortName") or symbol,
            "sector":          sector,
            "price":           round(price,2),
            "variation":       round(var_pct,2),
            "currency":        curr_sym,
            "is_pea":          is_pea,
            "country_flag":    country_flag,
            "country_name":    country_name,
            "rsi":             round(rsi_v,1),
            "rsi_signal":      rsi_sig,
            "macd_hist":       round(macd_h,6),
            "ema20":           round(ema20,2),
            "ema50":           round(ema50,2),
            "ichimoku_trend":  ichi_t,
            "volume_ratio":    round(vol_r,2),
            "fibonacci":       fib,
            "poc":             poc,
            "stop_loss":       stop,
            "take_profit":     tp,
            "tp_source":       tp_src,
            "tp_all":          tp_all,
            "consensus":       consensus,
            "consensus_warn":  consensus_warn,
            "nb_analysts":     nb_anal,
            "last_reco_date":  last_reco_date,
            "last_reco_age":   last_reco_age_days,
            "global_score":    global_score,
            "potentiel":       f"+{potentiel_pct:.1f}%" if potentiel_pct>=0 else f"{potentiel_pct:.1f}%",
            "stars":           stars,
            "weighted_average":weighted,
            "conviction_details": {
                "weighted_average": weighted,
                "categories": {
                    "technique":    {"stars": t_s,   "explanation": t_e},
                    "fondamentaux": {"stars": f_s,   "explanation": f_e},
                    "finances":     {"stars": fin_s, "explanation": fin_e},
                    "news":         {"stars": n_s,   "explanation": n_e},
                    "reseaux":      {"stars": soc_s, "explanation": soc_e},
                }
            },
            "tech_desc":    tech_desc,
            "about":        about_text,
            "insider":      insider_data,
            "events":       events,
            "patterns":     patterns,
            "chartLabels":  chart_labels,
            "chartPrices":  chart_prices,
            "news":         news_items,
        }, None   # (data, error_reason)
    except Exception as e:
        return None, f"erreur: {str(e)[:40]}"

# ================================================================
#  GÉNÉRATION HTML
# ================================================================

def f2(v, d=2):
    if v is None or (isinstance(v,(float,np.floating)) and np.isnan(v)): return "N/A"
    return f"{v:.{d}f}"

def conv_bars(details):
    cats   = details.get("categories",{})
    colors = {"technique":"#60a5fa","fondamentaux":"#10b981","finances":"#f59e0b",
              "news":"#a855f7","reseaux":"#ec4899"}
    bars = ""
    for key,col in colors.items():
        s   = int(cats.get(key,{}).get("stars",0))
        pct = int(s/4*100)
        bars += (f'<div style="height:10px;flex:1;background:rgba(255,255,255,.05);'
                 f'border-radius:5px;overflow:hidden;">'
                 f'<div style="height:100%;background:{col};width:{pct}%"></div></div>')
    return f'<div style="height:10px;display:flex;gap:4px;">{bars}</div>'

def stars_html(n):
    return "⭐" * max(0, min(4, int(n)))

def card_html(d):
    vc  = "up" if d["variation"]>=0 else "down"
    vs  = "+" if d["variation"]>=0 else ""
    st  = stars_html(d["stars"])
    is_wl  = d.get("is_watchlist", False)
    is_pea = d.get("is_pea", False)
    flag   = d.get("country_flag", "")
    cname  = d.get("country_name", "")
    wl_badge = ('<span style="background:#7c3aed22;color:#a78bfa;border:1px solid #7c3aed44;'
                'padding:2px 8px;border-radius:8px;font-size:.7em;font-weight:700;margin-left:6px;">'
                '👁 Watchlist</span>') if is_wl else ""
    pea_badge = ('<span style="background:#0ea5e922;color:#38bdf8;border:1px solid #0ea5e944;'
                 'padding:1px 7px;border-radius:6px;font-size:.68em;font-weight:700;margin-left:5px;">'
                 ' PEA</span>') if is_pea else ""
    flag_span = (f' <span title="{cname}">{flag}</span>' if flag else "")
    # Badges figures chartistes
    pat_badges = ""
    for p in (d.get("patterns") or [])[:2]:
        col = "#10b981" if p["strength"] == 3 else "#f59e0b"
        pat_badges += (f'<span style="background:{col}22;color:{col};border:1px solid {col}44;'
                       f'padding:2px 9px;border-radius:10px;font-size:.72em;font-weight:700;">'
                       f'{p["emoji"]} {p["name"]}</span>')
    pat_row = (f'<div style="display:flex;flex-wrap:wrap;gap:5px;margin-top:-10px;">{pat_badges}</div>'
               if pat_badges else "")
    border_style = "border-color:#7c3aed;border-width:2px;" if is_wl else ""
    return (
        f'<div class="card" onclick="openDetails(\'{d["ticker"]}\')" style="{border_style}">'
        f'<div class="card-header"><div>'
        f'<div class="ticker">{d["ticker"]} <span style="margin-left:8px;">{st}</span>{wl_badge}</div>'
        f'<div class="company-name">{d["name"]}</div>'
        f'<div style="font-size:.85em;color:var(--fg2);margin-top:6px;">'
        f'Score: {d["global_score"]} | {d["sector"]}{flag_span}{pea_badge}</div>'
        f'</div>'
        f'<div style="font-size:1em;color:#fbbf24;font-weight:800;">{d["weighted_average"]}/4</div></div>'
        f'<div style="text-align:right;">'
        f'<div class="price">{f2(d["price"])}{d["currency"]}</div>'
        f'<div class="variation {vc}">{vs}{f2(d["variation"])}%</div></div>'
        f'{conv_bars(d["conviction_details"])}'
        f'{pat_row}'
        f'<div style="display:flex;justify-content:space-between;padding-top:18px;'
        f'border-top:2px solid rgba(255,255,255,.05);font-size:1.05em;color:var(--fg2);">'
        f'<span>TP <span style="color:var(--green);font-weight:800;font-size:1.4em;">'
        f'{f2(d["take_profit"])}{d["currency"]}</span></span>'
        f'<span>Stop <span style="color:#ef4444;font-weight:700;">'
        f'{f2(d["stop_loss"])}{d["currency"]}</span></span></div></div>'
    )

def row_html(d):
    pc = "var(--green)" if "+" in d["potentiel"] else "#ef4444"
    st = stars_html(d["stars"])
    # Colonne Signaux : RSI + figures chartistes
    rsi_cell = d["rsi_signal"]
    for p in (d.get("patterns") or [])[:2]:
        col = "#10b981" if p["strength"] == 3 else "#f59e0b"
        rsi_cell += (f' <span style="background:{col}22;color:{col};border:1px solid {col}44;'
                     f'padding:1px 6px;border-radius:8px;font-size:.78em;font-weight:700;white-space:nowrap;">'
                     f'{p["emoji"]} {p["name"]}</span>')
    is_wl  = d.get("is_watchlist", False)
    is_pea = d.get("is_pea", False)
    flag   = d.get("country_flag", "")
    cname  = d.get("country_name", "")
    wl_td = ('<span style="background:#7c3aed22;color:#a78bfa;border:1px solid #7c3aed44;'
             'padding:1px 7px;border-radius:8px;font-size:.72em;font-weight:700;">👁 WL</span> '
             if is_wl else "")
    pea_td = (' <span style="background:#0ea5e922;color:#38bdf8;border:1px solid #0ea5e944;'
              'padding:1px 6px;border-radius:5px;font-size:.68em;font-weight:700;"> PEA</span>'
              if is_pea else "")
    flag_td = (f' <span title="{cname}" style="font-size:.9em;">{flag}</span>' if flag else "")
    row_style_attr = f' style="border-left:3px solid #7c3aed;cursor:pointer;"' if is_wl else ' style="cursor:pointer;"'
    return (
        f'<tr{row_style_attr} onclick="openDetails(\'{d["ticker"]}\')">'
        f'<td class="t-tk">{wl_td}{d["ticker"]}</td>'
        f'<td>{d["sector"]}{flag_td}{pea_td}</td>'
        f'<td class="t-num">{f2(d["price"])}{d["currency"]}</td>'
        f'<td class="t-tag">{d["consensus"]}</td>'
        f'<td class="t-rsi">{rsi_cell}</td>'
        f'<td class="t-src">{d["tp_source"]}</td>'
        f'<td class="t-num" style="color:var(--green);">{f2(d["take_profit"])}{d["currency"]}</td>'
        f'<td class="t-num" style="color:{pc};font-size:1.1em;font-weight:800;">{d["potentiel"]}</td>'
        f'<td class="t-num">{st} <span style="color:var(--fg2);font-size:.85em;">{d["weighted_average"]}/4</span></td></tr>'
    )

def build_html(stocks, date_str, time_str, markets):
    # Cartes ET tableau triés par potentiel décroissant
    def pot_val(d):
        try: return float(d["potentiel"].replace("+","").replace("%",""))
        except: return 0
    sorted_stocks = sorted(stocks, key=pot_val, reverse=True)
    cards   = "\n".join(card_html(d) for d in sorted_stocks)
    rows    = "\n".join(row_html(d)  for d in sorted_stocks)
    js_data = json.dumps({d["ticker"]:d for d in stocks}, ensure_ascii=False)
    # Badges marché avec labels lisibles et drapeaux
    MARKET_LABELS = {
        "CAC40":    "🇫🇷 CAC40",
        "DAX":      "🇩🇪 DAX",
        "AEX":      "🇳🇱 AEX",
        "IBEX":     "🇪🇸 IBEX",
        "FTSEMIB":  "🇮🇹 FTSE MIB",
        "FTSE100":  "🇬🇧 FTSE100",
        "NORDIC":   "🇸🇪 Nordic",
        "SP500":    "🇺🇸 SP500",
        "NASDAQ100":"🇺🇸 NASDAQ100",
        "US_GROWTH":"🇺🇸 US Growth",
    }
    badges = "".join(
        f'<span class="badge">{MARKET_LABELS.get(m, m)}</span>'
        for m in ["CAC40","DAX","AEX","IBEX","FTSEMIB","FTSE100","NORDIC","SP500","NASDAQ100","US_GROWTH"]
        if m in markets
    )

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Market Screener — {date_str}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root{{
  --bg:#0b0e11;--card:#151a21;--fg:#fff;--fg2:#9ca3af;
  --blue:#3b82f6;--green:#10b981;--red:#ef4444;--border:#2a303c;
}}
*{{margin:0;padding:0;box-sizing:border-box;font-family:'Inter',sans-serif;}}
body{{background:var(--bg);color:var(--fg);padding:40px 20px;font-size:20px;overflow-x:hidden;}}
.wrap{{max-width:1600px;margin:0 auto;}}
/* header */
header{{text-align:center;margin-bottom:40px;}}
h1{{font-size:3em;font-weight:800;background:linear-gradient(90deg,#fff,#9ca3af);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;margin-bottom:8px;}}
.sub{{color:var(--fg2);font-size:1.05em;}}
.badges{{display:inline-flex;gap:8px;margin-top:12px;flex-wrap:wrap;justify-content:center;}}
.badge{{background:rgba(59,130,246,.15);border:1px solid rgba(59,130,246,.3);
        color:var(--blue);padding:4px 14px;border-radius:20px;font-size:.8em;font-weight:700;}}
/* pages */
#page-dash{{display:block;}} #page-detail{{display:none;padding:10px;}}
/* tab nav */
.tab-nav{{display:flex;gap:8px;justify-content:center;margin-top:16px;}}
.tab-btn{{background:rgba(255,255,255,.06);border:1px solid var(--border);color:var(--fg2);
           padding:8px 24px;border-radius:20px;font-size:.85em;font-weight:600;cursor:pointer;
           transition:all .2s;}}
.tab-btn:hover,.tab-btn.active{{background:var(--blue);border-color:var(--blue);color:#fff;}}
/* table */
.tbl-wrap{{background:var(--card);border-radius:16px;border:2px solid var(--border);
           overflow-x:auto;margin-bottom:50px;padding:24px;}}
.tbl-wrap h2{{font-size:1.8em;font-weight:800;margin-bottom:22px;}}
table{{width:100%;border-collapse:collapse;min-width:900px;}}
th{{background:rgba(255,255,255,.04);color:var(--fg2);font-size:1em;font-weight:700;
    padding:16px 14px;text-align:left;border-bottom:2px solid var(--border);white-space:nowrap;}}
td{{padding:14px;border-bottom:1px solid rgba(255,255,255,.04);font-size:1em;vertical-align:middle;}}
tr:hover td{{background:rgba(59,130,246,.07);transition:background .15s;}}
tr:hover .t-tk{{color:var(--blue);}}
.t-tk{{font-weight:800;font-size:1.2em;white-space:nowrap;}}
.t-num{{font-weight:700;white-space:nowrap;}}
.t-tag{{font-weight:600;color:var(--fg2);}}
.t-rsi{{white-space:nowrap;font-size:.9em;}}
.t-src{{font-style:italic;color:var(--fg2);font-size:.85em;white-space:nowrap;}}
/* grid cards */
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:28px;margin-bottom:60px;}}
.card{{background:var(--card);border-radius:20px;padding:32px;border:2px solid var(--border);
       display:flex;flex-direction:column;gap:22px;cursor:pointer;
       transition:all .25s cubic-bezier(.4,0,.2,1);}}
.card:hover{{transform:scale(1.02);box-shadow:0 20px 50px rgba(0,0,0,.6);border-color:var(--blue);}}
.card-header{{display:flex;justify-content:space-between;align-items:flex-start;}}
.ticker{{font-size:1.5em;font-weight:900;color:#fff;}}
.company-name{{font-size:.7em;color:var(--fg2);font-weight:500;display:block;margin-top:5px;}}
.price{{font-size:2.2em;font-weight:800;}}
.variation{{font-size:1.2em;font-weight:700;margin-top:4px;}}
.variation.up{{color:var(--green);}} .variation.down{{color:var(--red);}}
/* detail page */
.back-btn{{background:#1e293b;border:2px solid var(--border);color:#fff;padding:14px 28px;
           font-size:1.1em;font-weight:700;border-radius:12px;cursor:pointer;margin-bottom:36px;
           display:inline-flex;align-items:center;gap:12px;transition:all .2s;}}
.back-btn:hover{{background:#334155;transform:translateX(-4px);}}
.d-header{{display:flex;justify-content:space-between;align-items:flex-end;
           border-bottom:3px solid var(--border);padding-bottom:28px;margin-bottom:36px;flex-wrap:wrap;gap:16px;}}
.d-ticker{{font-size:1.5em;color:var(--blue);font-weight:700;}}
.d-name{{font-size:2.6em;font-weight:800;line-height:1.1;}}
.d-price{{font-size:2.8em;font-weight:800;text-align:right;}}
.d-var{{font-size:1.4em;font-weight:700;text-align:right;margin-top:4px;}}
.d-grid{{display:grid;grid-template-columns:60fr 40fr;gap:40px;}}
@media(max-width:900px){{.d-grid{{grid-template-columns:1fr;}}}}
.panel{{background:var(--card);border-radius:18px;padding:28px;border:2px solid var(--border);margin-bottom:28px;}}
.panel h3{{font-size:1.3em;font-weight:800;margin-bottom:20px;}}
.strat-row{{display:flex;justify-content:space-between;padding:12px 0;
            border-bottom:1px solid #232936;color:var(--fg2);font-size:1em;}}
.strat-row:last-child{{border-bottom:none;}}
.sv{{color:#fff;font-weight:700;font-size:1.1em;}} .sv.green{{color:var(--green);}} .sv.blue{{color:var(--blue);}} .sv.red{{color:var(--red);}}
/* Fibonacci */
.fib-ladder{{display:flex;flex-direction:column;gap:7px;margin-top:14px;}}
.fib-lvl{{display:flex;justify-content:space-between;padding:10px 16px;
          background:rgba(255,255,255,.03);border-radius:9px;font-size:1em;font-weight:600;
          border:1px solid rgba(255,255,255,.05);}}
.fib-lvl.res{{border-left:6px solid var(--red);color:#fca5a5;}}
.fib-lvl.sup{{border-left:6px solid var(--green);color:#6ee7b7;}}
.fib-lvl.cur{{background:var(--blue);color:#fff;font-weight:800;transform:scale(1.02);
              box-shadow:0 8px 28px rgba(59,130,246,.4);margin:8px 0;}}
/* tech table */
.tech-row{{display:flex;justify-content:space-between;padding:12px 0;
           border-bottom:1px solid rgba(255,255,255,.05);font-size:1em;}}
.tech-row:last-child{{border-bottom:none;}}
/* news */
.news-item{{margin-bottom:16px;padding-bottom:16px;border-bottom:1px solid #232936;}}
.news-item:last-child{{border-bottom:none;margin-bottom:0;}}
</style>
</head>
<body>

<!-- DASHBOARD -->
<div id="page-dash">
<div class="wrap">
  <header>
    <h1>⚡ MARKET SCREENER</h1>
    <div class="sub">{date_str} — Actualisé à <span style="color:var(--blue)">{time_str}</span></div>
    <div class="badges">{badges}<span class="badge">{len(stocks)} opportunités</span></div>
    <div class="tab-nav" id="main-tab-nav">
      <button id="tab-btn-recap"  class="tab-btn active" onclick="showTab('recap')">📋 Récapitulatif</button>
      <button id="tab-btn-cartes" class="tab-btn"        onclick="showTab('cartes')">🃏 Cartes</button>
    </div>
  </header>

  <div id="section-recap">
  <div class="tbl-wrap">
    <h2>📋 Récapitulatif — Top {len(stocks)}</h2>
    <table>
      <thead><tr>
        <th>Ticker</th><th>Secteur</th><th>Prix</th><th>Consensus</th>
        <th>Signal RSI</th><th>Base Objectif</th><th>Objectif</th>
        <th>Potentiel</th><th>Conviction</th>
      </tr></thead>
      <tbody>{rows}</tbody>
    </table>
    <div style="text-align:right;margin-top:10px;font-size:.78em;color:var(--fg2);font-style:italic;">
      👆 Cliquez sur une ligne pour voir l'analyse détaillée
    </div>
  </div>
  </div>

  <div id="section-cartes" style="display:none;">
  <div class="grid">{cards}</div>
  </div>

  <!-- Footer -->
  <div style="margin-top:40px;padding:24px 30px;border-top:1px solid var(--border);
              color:var(--fg2);font-size:.82em;">
    <div style="margin-bottom:10px;">
      ⚡ Généré le {date_str} à {time_str} — Données yfinance / StockTwits
    </div>
    <div style="margin-bottom:10px;">
      <span style="background:#7c3aed22;color:#a78bfa;border:1px solid #7c3aed44;
                   padding:2px 8px;border-radius:8px;font-size:.85em;font-weight:700;
                   margin-right:8px;">👁 WL</span>
      <span>Watchlist personnalisée — actions suivies en priorité, analysées même hors top {TOP_N}.</span>
    </div>
    <div style="font-size:.78em;opacity:.5;">
      ⚠️ Analyse algorithmique — pas un conseil en investissement.
    </div>
  </div>
</div>
</div>

<!-- DETAIL PAGE -->
<div id="page-detail">
<div class="wrap">
  <button class="back-btn" onclick="closeDet()">&#8592; Retour au screener</button>

  <div class="d-header">
    <div>
      <div class="d-ticker" id="d-tick"></div>
      <div class="d-name" id="d-name"></div>
    </div>
    <div>
      <div class="d-price" id="d-price"></div>
      <div class="d-var"   id="d-var"></div>
    </div>
  </div>

  <div class="d-grid">
    <!-- LEFT -->
    <div>
      <div class="panel">
        <h3>📈 Graphique ({CHART_BARS}j)</h3>
        <div style="height:300px;"><canvas id="bigChart"></canvas></div>
      </div>
      <div class="panel">
        <h3>⚙️ Indicateurs Techniques</h3>
        <div id="d-tech"></div>
        <p style="margin-top:14px;color:var(--fg2);font-size:.85em;font-style:italic;" id="d-tech-desc"></p>
      </div>
      <div class="panel" id="d-patterns-panel">
        <h3>📊 Figures Chartistes</h3>
        <div id="d-patterns" style="margin-top:6px;"></div>
      </div>
      <div class="panel">
        <h3>🏢 À propos de la société</h3>
        <div id="d-about" style="color:var(--fg2);font-size:.9em;line-height:1.6;"></div>
      </div>
      <div class="panel" id="d-insider-panel">
        <h3>👔 Transactions Dirigeants</h3>
        <div id="d-insider" style="margin-top:6px;"></div>
      </div>
      <div class="panel" id="d-events-panel">
        <h3>📅 Calendrier des Événements</h3>
        <div id="d-events" style="margin-top:6px;"></div>
      </div>
    </div>

    <!-- RIGHT -->
    <div>
      <div class="panel">
        <h3>🎯 Stratégie</h3>
        <div class="strat-row"><span>Entrée</span><span class="sv blue" id="d-entry"></span></div>
        <div class="strat-row"><span>Stop Loss (2×ATR)</span><span class="sv red" id="d-stop"></span></div>
        <div class="strat-row"><span>Take Profit principal</span><span class="sv green" id="d-tp"></span></div>
        <div class="strat-row"><span>Horizon TP</span><span class="sv" id="d-tp-horizon"></span></div>
        <div class="strat-row"><span>Potentiel</span><span class="sv green" id="d-pot"></span></div>
        <div class="strat-row"><span>Analystes</span><span class="sv" id="d-cons"></span></div>
        <div class="strat-row" id="d-reco-date-row" style="display:none;">
          <span style="color:var(--fg2);font-size:.85em;">Dernière note</span>
          <span class="sv" style="font-size:.85em;" id="d-reco-date"></span>
        </div>
        <div id="d-cons-warn" style="display:none;margin-top:10px;padding:10px 14px;
             background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);
             border-radius:10px;font-size:.85em;color:#fbbf24;line-height:1.5;"></div>
        <div id="d-tp-all" style="margin-top:14px;"></div>
      </div>

      <div class="panel">
        <h3>⭐ Conviction — <span style="color:#fbbf24;" id="d-conv-avg"></span></h3>
        <div id="d-conv-grid" style="margin-top:14px;"></div>
      </div>

      <div class="panel">
        <h3>📐 Niveaux Fibonacci</h3>
        <div class="fib-ladder" id="d-fib"></div>
      </div>

      <div class="panel">
        <h3>📰 News & Catalyseurs</h3>
        <div id="d-news" style="margin-top:12px;"></div>
      </div>
    </div>
  </div>
</div>
</div>

<script>
const D = {js_data};
let chart = null;

function fx(v,d=2){{ const n=parseFloat(v); return isNaN(n)?'N/A':n.toFixed(d); }}
function stars(n){{ return '⭐'.repeat(Math.max(0,Math.min(4,parseInt(n)||0))); }}

window.openDetails = function(tk){{
  const d = D[tk]; if(!d){{alert('Données manquantes');return;}}
  const c = d.currency||'';

  document.getElementById('d-tick').innerText  = d.ticker;
  document.getElementById('d-name').innerText  = d.name||'';
  document.getElementById('d-price').innerText = fx(d.price)+c;
  document.getElementById('d-entry').innerText = fx(d.price)+c;
  document.getElementById('d-stop').innerText  = fx(d.stop_loss)+c;
  document.getElementById('d-tp').innerText    = fx(d.take_profit)+c+' — '+( d.tp_source||'');
  document.getElementById('d-pot').innerText   = d.potentiel||'';
  document.getElementById('d-cons').innerText  = (d.consensus||'') +
    (d.nb_analysts ? ` (${{d.nb_analysts}} analystes)` : '');

  // Date de la dernière recommandation analyste
  const recoDateRow = document.getElementById('d-reco-date-row');
  const recoDateEl  = document.getElementById('d-reco-date');
  if (d.last_reco_date) {{
    recoDateRow.style.display = 'flex';
    const age = d.last_reco_age;
    let ageCol = 'var(--fg2)';
    let ageIcon = '';
    if (age !== null && age !== undefined) {{
      if      (age < 30)  {{ ageCol = '#10b981'; ageIcon = ' ✅'; }}
      else if (age < 90)  {{ ageCol = '#f59e0b'; ageIcon = ''; }}
      else                {{ ageCol = '#ef4444'; ageIcon = ' ⚠️'; }}
    }}
    recoDateEl.innerHTML = `<span style="color:${{ageCol}}">${{d.last_reco_date}}${{ageIcon}}</span>` +
      (age !== null && age !== undefined ? ` <span style="color:var(--fg2);font-size:.8em;">(il y a ${{age}}j)</span>` : '');
  }} else {{
    recoDateRow.style.display = 'none';
  }}

  // Horizon TP
  const horizonEl = document.getElementById('d-tp-horizon');
  if (d.tp_source && d.tp_source.includes('nalyste')) {{
    horizonEl.innerText = '12 mois (objectif consensuel)';
    horizonEl.style.color = '#60a5fa';
  }} else {{
    horizonEl.innerText = 'Technique (pas de durée définie)';
    horizonEl.style.color = 'var(--fg2)';
  }}

  // Alerte staleness consensus
  const warnEl = document.getElementById('d-cons-warn');
  if (d.consensus_warn) {{
    warnEl.innerText = d.consensus_warn;
    warnEl.style.display = 'block';
  }} else {{
    warnEl.style.display = 'none';
  }}

  // Tous les objectifs de prix disponibles
  const tpAllEl = document.getElementById('d-tp-all');
  const tpAll = d.tp_all || [];
  if (tpAll.length > 1) {{
    const srcLabel = src => {{
      if (src.includes('haut')) return '🔝';
      if (src.includes('Fibonacci 127')) return '📐';
      if (src.includes('Fibonacci 161')) return '📐';
      if (src.includes('Fibonacci 261')) return '📐';
      if (src.includes('52')) return '📊';
      if (src.includes('nalyste')) return '👥';
      return '•';
    }};
    tpAllEl.innerHTML = '<div style="font-size:.85em;color:var(--fg2);margin-bottom:8px;font-weight:600;">Autres objectifs disponibles :</div>' +
      tpAll.map(tp => {{
        const pct = ((tp.val - parseFloat(d.price)) / parseFloat(d.price) * 100).toFixed(1);
        const col = parseFloat(pct) > 50 ? '#10b981' : parseFloat(pct) > 20 ? '#60a5fa' : 'var(--fg2)';
        return `<div style="display:flex;justify-content:space-between;padding:5px 0;
                border-bottom:1px solid rgba(255,255,255,.04);font-size:.85em;">
          <span style="color:var(--fg2)">${{srcLabel(tp.src)}} ${{tp.src}}</span>
          <span style="color:${{col}};font-weight:700;">${{fx(tp.val)}} ${{c}} &nbsp;<span style="font-size:.85em;opacity:.8;">+${{pct}}%</span></span>
        </div>`;
      }}).join('');
  }} else {{
    tpAllEl.innerHTML = '';
  }}

  const vEl = document.getElementById('d-var');
  const v = parseFloat(d.variation);
  vEl.innerText = (v>=0?'+':'')+v.toFixed(2)+'%';
  vEl.style.color = v>=0?'#10b981':'#ef4444';

  const rv = parseFloat(d.rsi);
  const rc = rv<30?'#ef4444':rv>70?'#f59e0b':'#10b981';
  const mv = parseFloat(d.macd_hist);
  const mc = mv>0?'#10b981':'#ef4444';
  const ich = d.ichimoku_trend||'N/A';
  const ic = ich==='Haussier'?'#10b981':ich==='Baissier'?'#ef4444':'#f59e0b';

  document.getElementById('d-tech-desc').innerText = d.tech_desc||'';

  // Helper row (déclaré ICI pour éviter tout problème d'hoisting)
  function row(label, val){{
    return `<div class="tech-row"><span style="color:var(--fg2)">${{label}}</span><span>${{val}}</span></div>`;
  }}

  document.getElementById('d-tech').innerHTML =
    row('Nuage Ichimoku',`<span style="color:${{ic}};font-weight:700">${{ich}}</span>`) +
    row('RSI (14)',`<span style="color:${{rc}};font-weight:700">${{fx(rv,1)}}</span>`) +
    row('MACD',`<span style="color:${{mc}};font-weight:700">${{mv>0?'▲ Haussier':'▼ Baissier'}} (${{fx(mv,4)}})</span>`) +
    row('Ratio Volume',`<span style="color:${{parseFloat(d.volume_ratio)>2?'#10b981':'#fff'}};font-weight:700">${{fx(d.volume_ratio,2)}}x</span>`) +
    row('EMA 20 / EMA 50',`${{fx(d.ema20)}} / ${{fx(d.ema50)}}`) +
    row('POC (MA20 proxy)',`<span style="color:#a78bfa;font-weight:700">${{fx(d.poc)}}</span>`);

  // Figures chartistes
  const pats = d.patterns || [];
  const pEl  = document.getElementById('d-patterns');
  if (!pEl) return;
  if (pats.length === 0) {{
    pEl.innerHTML = '<span style="color:var(--fg2);font-size:.9em">Aucune figure chartiste detectee.</span>';
  }} else {{
    const sCol = s => s===3?'#10b981':s===2?'#f59e0b':'#9ca3af';
    const sLbl = s => s===3?'Fort':'Modere';
    pEl.innerHTML = pats.map(p => `
      <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 0;
                  border-bottom:1px solid rgba(255,255,255,.05);">
        <span style="font-size:1.5em;line-height:1.2">${{p.emoji}}</span>
        <div style="flex:1">
          <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
            <span style="font-weight:700;color:#fff">${{p.name}}</span>
            <span style="background:${{sCol(p.strength)}}22;color:${{sCol(p.strength)}};
                         border:1px solid ${{sCol(p.strength)}}55;padding:2px 8px;
                         border-radius:10px;font-size:.75em;font-weight:700;">${{sLbl(p.strength)}}</span>
          </div>
          <div style="font-size:.82em;color:var(--fg2);line-height:1.4">${{p.desc}}</div>
        </div>
      </div>`).join('');
  }}

  // ── À propos de la société ───────────────────────────────────
  const aboutEl = document.getElementById('d-about');
  if (aboutEl) {{
    if (d.about && d.about.length > 10) {{
      aboutEl.innerHTML = `<p style="margin:0">${{d.about}}</p>`;
    }} else {{
      aboutEl.innerHTML = '<span style="color:var(--fg2);font-size:.9em;font-style:italic;">Description non disponible.</span>';
    }}
  }}

  // ── Transactions Dirigeants ──────────────────────────────────
  const insiderEl    = document.getElementById('d-insider');
  const insiderPanel = document.getElementById('d-insider-panel');
  if (insiderEl) {{
    const ins = d.insider || [];
    if (ins.length === 0) {{
      insiderEl.innerHTML = '<span style="color:var(--fg2);font-size:.9em;font-style:italic;">Aucune transaction de dirigeant disponible.</span>';
    }} else {{
      // Résumé : nb achats vs ventes
      const nBuy  = ins.filter(x=>x.is_buy).length;
      const nSell = ins.filter(x=>x.is_sell).length;
      const sumBuy = ins.filter(x=>x.is_buy).reduce((a,b)=>a+(b.value||0),0);
      const sumSell= ins.filter(x=>x.is_sell).reduce((a,b)=>a+(b.value||0),0);

      let summaryHtml = `<div style="display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap;">`;
      if (nBuy > 0) summaryHtml += `
        <div style="background:#10b98115;border:1px solid #10b98133;border-radius:10px;
                    padding:8px 16px;text-align:center;">
          <div style="color:#10b981;font-weight:800;font-size:1.2em">▲ ${{nBuy}} achat${{nBuy>1?'s':''}}</div>
          <div style="color:var(--fg2);font-size:.8em">${{sumBuy>0?'~'+fx(sumBuy/1000,0)+'K '+c:''}}</div>
        </div>`;
      if (nSell > 0) summaryHtml += `
        <div style="background:#ef444415;border:1px solid #ef444433;border-radius:10px;
                    padding:8px 16px;text-align:center;">
          <div style="color:#ef4444;font-weight:800;font-size:1.2em">▼ ${{nSell}} vente${{nSell>1?'s':''}}</div>
          <div style="color:var(--fg2);font-size:.8em">${{sumSell>0?'~'+fx(sumSell/1000,0)+'K '+c:''}}</div>
        </div>`;
      summaryHtml += `</div>`;

      const rowsHtml = ins.slice(0,6).map(tx => {{
        const col = tx.is_buy ? '#10b981' : tx.is_sell ? '#ef4444' : 'var(--fg2)';
        const icon= tx.is_buy ? '▲' : tx.is_sell ? '▼' : '•';
        const sharesStr = tx.shares > 0 ? `${{tx.shares.toLocaleString()}} titres` : '';
        const valStr    = tx.value  > 0 ? `≈ ${{fx(tx.value/1000,0)}}K ${{c}}` : '';
        return `<div style="display:grid;grid-template-columns:70px 1fr auto;gap:8px;
                            align-items:center;padding:9px 0;
                            border-bottom:1px solid rgba(255,255,255,.05);font-size:.88em;">
          <span style="color:var(--fg2);font-size:.85em">${{tx.date}}</span>
          <div>
            <div style="font-weight:600;color:#fff">${{tx.name||'Dirigeant'}}</div>
            <div style="font-size:.82em;color:var(--fg2)">${{tx.type}}</div>
          </div>
          <div style="text-align:right">
            <div style="color:${{col}};font-weight:700">${{icon}} ${{sharesStr}}</div>
            <div style="font-size:.82em;color:var(--fg2)">${{valStr}}</div>
          </div>
        </div>`;
      }}).join('');

      insiderEl.innerHTML = summaryHtml + rowsHtml;
    }}
  }}

  // ── Calendrier des Événements ────────────────────────────────
  const evtsEl = document.getElementById('d-events');
  if (evtsEl) {{
    const evts = d.events || [];
    if (evts.length === 0) {{
      evtsEl.innerHTML = '<span style="color:var(--fg2);font-size:.9em;font-style:italic;">Aucun événement trouvé (résultats, dividende...).</span>';
    }} else {{
      evtsEl.innerHTML = evts.map(ev => `
        <div style="display:flex;align-items:center;gap:14px;padding:10px 0;
                    border-bottom:1px solid rgba(255,255,255,.05);">
          <span style="font-size:1.5em;">${{ev.emoji}}</span>
          <div style="flex:1">
            <div style="font-weight:600;color:#fff;font-size:.9em">${{ev.label}}</div>
          </div>
          <span style="font-weight:700;color:#60a5fa;font-size:.9em;white-space:nowrap;">${{ev.date}}</span>
        </div>`).join('');
    }}
  }}

  const cats = (d.conviction_details||{{}}).categories||{{}};
  const ord = [
    {{id:'technique',   lbl:'⚙️ Technique',       col:'#60a5fa'}},
    {{id:'fondamentaux',lbl:'📊 Fondamentaux',     col:'#10b981'}},
    {{id:'finances',    lbl:'💰 Finances',          col:'#f59e0b'}},
    {{id:'news',        lbl:'📰 News & Sentiment',  col:'#a855f7'}},
    {{id:'reseaux',     lbl:'💬 Réseaux (ST)',      col:'#ec4899'}},
  ];
  let ch='';
  ord.forEach(o=>{{
    const cat  = cats[o.id]||{{}};
    const ns   = parseInt(cat.stars)||0;
    const expl = cat.explanation||'N/A';
    const pct  = ns/4*100;
    ch += `<div style="margin-bottom:14px;">
      <div style="display:flex;justify-content:space-between;margin-bottom:6px;">
        <span style="font-weight:700;color:#fff;font-size:.9em">${{o.lbl}}</span>
        <span style="color:#fbbf24;font-size:.9em">${{stars(ns)}} <span style="color:var(--fg2);font-size:.8em">${{ns}}/4</span></span>
      </div>
      <div style="height:6px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden;margin-bottom:6px;">
        <div style="height:100%;background:${{o.col}};width:${{pct}}%;transition:width .4s ease"></div>
      </div>
      <div style="font-size:.78em;color:var(--fg2);font-style:italic;line-height:1.4">${{expl}}</div>
    </div>`;
  }});
  document.getElementById('d-conv-grid').innerHTML = ch;
  document.getElementById('d-conv-avg').innerText  = (d.conviction_details?.weighted_average||0)+' / 4';

  // Fibonacci
  const fib = d.fibonacci||{{}};
  const pr  = parseFloat(d.price)||0;
  let lvls  = [];
  if(fib.high_ref) lvls.push({{n:'Point Haut (Ref)',v:fib.high_ref}});
  if(fib.low_ref)  lvls.push({{n:'Point Bas (Ref)', v:fib.low_ref}});
  if(fib.retracements) Object.entries(fib.retracements).forEach(([k,v])=>
    lvls.push({{n:'Fib '+(parseFloat(k.replace('fib_',''))/10)+'%',v}}));
  if(fib.extensions)   Object.entries(fib.extensions).forEach(([k,v])=>
    lvls.push({{n:'Ext '+(parseFloat(k.replace('ext_',''))/10)+'%',v}}));
  lvls.push({{n:'PRIX ACTUEL',v:pr,cur:true}});
  if(d.poc) lvls.push({{n:'POC (MA20)',v:parseFloat(d.poc)}});
  lvls = lvls.filter((x,i,a)=>a.findIndex(y=>y.v===x.v&&y.n===x.n)===i);
  lvls.sort((a,b)=>b.v-a.v);
  let fh='';
  lvls.forEach(l=>{{
    const lv=parseFloat(l.v);
    let cl='',sf='';
    if(l.cur)        {{cl='cur';}}
    else if(lv>pr)   {{cl='res';sf=' (Rés.)';}}
    else             {{cl='sup';sf=' (Sup.)';}}
    if(l.n.includes('Point')) sf='';
    fh+=`<div class="fib-lvl ${{cl}}"><span>${{l.n}}${{sf}}</span><span>${{fx(l.v)}} ${{c}}</span></div>`;
  }});
  document.getElementById('d-fib').innerHTML = fh;

  // News
  const nd = document.getElementById('d-news');
  if(d.news && d.news.length>0){{
    nd.innerHTML = d.news.slice(0,3).map(n=>{{
      const t = n.url
        ? `<a href="${{n.url}}" target="_blank" style="color:var(--blue);text-decoration:none;">${{n.title}}</a>`
        : `<span style="color:#fff">${{n.title}}</span>`;
      return `<div class="news-item"><div style="font-weight:600">${{t}}</div>
        <div style="font-size:.8em;color:var(--fg2);margin-top:4px">${{n.date||''}}</div></div>`;
    }}).join('');
  }} else {{
    nd.innerHTML = '<span style="color:var(--fg2);font-size:.9em">Aucune news récente disponible.</span>';
  }}

  // Chart
  if(d.chartLabels&&d.chartPrices){{
    if(chart)chart.destroy();
    const ctx=document.getElementById('bigChart').getContext('2d');
    const g=ctx.createLinearGradient(0,0,0,300);
    g.addColorStop(0,'rgba(16,185,129,.18)');g.addColorStop(1,'rgba(16,185,129,0)');
    chart=new Chart(ctx,{{type:'line',
      data:{{labels:d.chartLabels,datasets:[{{label:'Price',data:d.chartPrices,
        borderColor:'#10b981',borderWidth:3,backgroundColor:g,fill:true,pointRadius:0,tension:.35}}]}},
      options:{{responsive:true,maintainAspectRatio:false,plugins:{{legend:{{display:false}}}},
        scales:{{x:{{grid:{{color:'rgba(255,255,255,.04)'}},ticks:{{font:{{size:11}}}}}},
                 y:{{grid:{{color:'rgba(255,255,255,.04)'}},position:'right',ticks:{{font:{{size:11}}}}}}}}}}
    }});
  }}

  document.getElementById('page-dash').style.display='none';
  document.getElementById('page-detail').style.display='block';
  window.scrollTo(0,0);
}};

window.closeDet=function(){{
  document.getElementById('page-dash').style.display='block';
  document.getElementById('page-detail').style.display='none';
  window.scrollTo(0,0);
}};

// Navigation onglets tableau / cartes
window.showTab = function(tab) {{
  const recap  = document.getElementById('section-recap');
  const cartes = document.getElementById('section-cartes');
  const btn0   = document.getElementById('tab-btn-recap');
  const btn1   = document.getElementById('tab-btn-cartes');
  if (!recap || !cartes) return;
  if (tab === 'recap') {{
    recap.style.display  = 'block';
    cartes.style.display = 'none';
    if(btn0) btn0.classList.add('active');
    if(btn1) btn1.classList.remove('active');
  }} else {{
    recap.style.display  = 'none';
    cartes.style.display = 'block';
    if(btn0) btn0.classList.remove('active');
    if(btn1) btn1.classList.add('active');
  }}
}};
</script>
</body></html>"""

# ================================================================
#  MAIN
# ================================================================

def main():
    now      = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")

    print(f"\n{'='*56}")
    print(f"  STOCK SCREENER v3       {date_str}  {time_str}")
    print(f"  Marches : {', '.join(MARKETS)}")
    print(f"  Top {TOP_N} opportunites recherchees")
    print(f"{'='*56}\n")

    universe, watchlist_set = get_universe(MARKETS)
    candidates = quick_scan(universe)

    # Forcer les tickers watchlist en phase 2 même si absents du scan
    for wt in watchlist_set:
        if wt not in candidates:
            candidates.insert(0, wt)
            print(f"  + Watchlist forcée : {wt}")

    if not candidates:
        print("Aucun candidat. Verifiez votre connexion."); return

    print(f"{'─'*56}")
    print(f"  PHASE 2 — Analyse profonde ({len(candidates)} candidats)")
    print(f"  (Technique / Fondamentaux / Finances / News / Social)")
    print(f"{'─'*56}")

    stocks        = []
    watchlist_done = {}  # ticker → résultat pour les tickers watchlist

    for i, sym in enumerate(candidates, 1):
        print(f"  [{i:02d}/{len(candidates)}] {sym:<14}", end=" ", flush=True)
        is_wl = sym in watchlist_set

        r, reason = analyze(sym, force_include=is_wl)
        if r:
            if is_wl:
                watchlist_done[sym] = r
                print(f"OK  score={r['global_score']:.1f}  {'★'*r['stars']}  conv={r['weighted_average']}/4  [watchlist]")
            else:
                stocks.append(r)
                print(f"OK  score={r['global_score']:.1f}  {'★'*r['stars']}  conv={r['weighted_average']}/4")
        else:
            # Afficher la raison seulement si c'est une vraie erreur (pas un filtre)
            if reason and "potentiel" not in reason and "volume" not in reason \
               and "capi" not in reason and "prix" not in reason:
                print(f"--  {reason}")
            else:
                print(f"--  filtré" if reason else "--")

        # Stopper seulement quand le TOP_N est atteint ET toute la watchlist est traitée
        remaining_wl = watchlist_set - set(watchlist_done.keys())
        remaining_wl_in_queue = [c for c in candidates[i:] if c in remaining_wl]
        if len(stocks) >= TOP_N and not remaining_wl_in_queue:
            print(f"\n  {TOP_N} actions retenues + watchlist complète.")
            break

    if not stocks and not watchlist_done:
        print("Aucune action analysee."); return

    # Rassembler TOUT dans un pool unique
    all_results = {}
    for s in stocks:
        s["is_watchlist"] = False
        all_results[s["ticker"]] = s
    for sym, r in watchlist_done.items():
        r["is_watchlist"] = True   # toujours marqué WL
        all_results[sym] = r

    # Tri global par score décroissant
    sorted_all = sorted(all_results.values(), key=lambda x: x["global_score"], reverse=True)

    # Top TOP_N : les meilleurs scores (WL ou pas)
    top_stocks  = sorted_all[:TOP_N]
    top_tickers = {s["ticker"] for s in top_stocks}

    # Watchlist hors top : toujours affichées en plus
    wl_extra = []
    for sym in watchlist_set:
        if sym in all_results and sym not in top_tickers:
            r = all_results[sym]
            r["is_watchlist"]   = True
            r["watchlist_only"] = True  # apparaît en bas, hors classement
            wl_extra.append(r)
    wl_extra.sort(key=lambda x: x["global_score"], reverse=True)

    # Pour les WL qui sont dans le top : marquer watchlist_only=False
    # mais conserver is_watchlist=True pour le badge
    for s in top_stocks:
        s["watchlist_only"] = False

    final_stocks = top_stocks + wl_extra
    total = len(final_stocks)
    wl_in_top    = sum(1 for s in top_stocks if s.get("is_watchlist"))
    wl_extra_cnt = len(wl_extra)

    html = build_html(final_stocks, date_str, time_str, MARKETS)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"\n{'='*56}")
    print(f"  Rapport genere : {OUTPUT_FILE}")
    print(f"  {total} actions ({TOP_N} top + {wl_extra_cnt} watchlist exclusives)")
    print(f"  WL dans le top : {wl_in_top}")
    print(f"  Top 5 :")
    for i,s in enumerate(final_stocks[:5],1):
        wl_tag = " [WL]" if s.get("is_watchlist") else ""
        print(f"    {i}. {s['ticker']:<12} score={s['global_score']:.1f}  pot={s['potentiel']}  {'★'*s['stars']}{wl_tag}")
    print(f"{'='*56}\n")

if __name__ == "__main__":
    main()

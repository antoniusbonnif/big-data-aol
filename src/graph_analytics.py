"""Graph A (spasial-temporal zona) dan Graph B (bipartite wilayah-karakteristik)."""
import math

import networkx as nx
import pandas as pd


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    """Jarak great-circle (km). Dipakai daripada geopy.distance -- lebih cepat
    untuk dipanggil ribuan kali dalam loop, akurasi cukup untuk grid 1 derajat."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def build_zone_centroids(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby("zone_id")
        .agg(lat=("latitude", "mean"), lon=("longitude", "mean"), event_count=("event_id", "count"))
        .reset_index()
    )


def build_graph_a(df: pd.DataFrame, max_distance_km: float = 200, max_days: int = 7) -> nx.Graph:
    """
    Node = zona seismik (grid 1 derajat). Edge = pasangan event di zona berbeda
    yang jaraknya <=max_distance_km DAN selisih waktu <=max_days (proxy rantai
    aftershock / migrasi aktivitas seismik antar zona).

    Kompleksitas dijaga O(n log n) bukan O(n^2): event diurutkan per waktu,
    dicek hanya terhadap event dalam window waktu ke depan (sliding window),
    bukan seluruh pasangan event.
    """
    df_sorted = df.sort_values("time_utc").reset_index(drop=True)
    zone_centroids = build_zone_centroids(df).set_index("zone_id")

    G = nx.Graph()
    for zone_id, row in zone_centroids.iterrows():
        G.add_node(zone_id, lat=row["lat"], lon=row["lon"], event_count=int(row["event_count"]))

    times = df_sorted["time_utc"].values
    zones = df_sorted["zone_id"].values
    n = len(df_sorted)
    window = pd.Timedelta(days=max_days)

    edge_weight = {}
    j_start = 0
    for i in range(n):
        t_i = df_sorted.loc[i, "time_utc"]
        while j_start < n and df_sorted.loc[j_start, "time_utc"] < t_i - window:
            j_start += 1
        j = i + 1
        while j < n and df_sorted.loc[j, "time_utc"] <= t_i + window:
            if zones[i] != zones[j]:
                z1, z2 = zone_centroids.loc[zones[i]], zone_centroids.loc[zones[j]]
                dist = _haversine_km(z1["lat"], z1["lon"], z2["lat"], z2["lon"])
                if dist <= max_distance_km:
                    key = tuple(sorted((zones[i], zones[j])))
                    edge_weight[key] = edge_weight.get(key, 0) + 1
            j += 1

    for (z1, z2), w in edge_weight.items():
        G.add_edge(z1, z2, weight=w)
    return G


def compute_graph_a_metrics(G: nx.Graph) -> pd.DataFrame:
    degree = dict(G.degree())
    betweenness = nx.betweenness_centrality(G, weight="weight")
    eigenvector = nx.eigenvector_centrality(G, weight="weight", max_iter=1000)
    pagerank = nx.pagerank(G, weight="weight")

    return pd.DataFrame({
        "zone_id": list(degree.keys()),
        "degree": list(degree.values()),
        "betweenness": [betweenness[z] for z in degree],
        "eigenvector": [eigenvector[z] for z in degree],
        "pagerank": [pagerank[z] for z in degree],
    }).sort_values("pagerank", ascending=False)


def detect_communities(G: nx.Graph) -> dict:
    """Louvain community detection. Return {node: community_id}.

    Pakai networkx.community.louvain_communities (built-in sejak networkx 2.8+)
    daripada paket python-louvain terpisah -- nama modul python-louvain (`import
    community`) collide dengan paket PyPI lain bernama sama, yang di beberapa
    environment (termasuk Colab) bisa ke-install duluan dan menimpa python-louvain
    tanpa API best_partition. networkx native menghindari masalah ini sepenuhnya.
    """
    communities = nx.community.louvain_communities(G, weight="weight", seed=42)
    partition = {}
    for community_id, nodes in enumerate(communities):
        for node in nodes:
            partition[node] = community_id
    return partition


def build_graph_b(df: pd.DataFrame) -> nx.Graph:
    """
    Bipartite: node wilayah (zone_id) di satu sisi, node kategori
    (depth_class, mag_band, tsunami-flag) di sisi lain. Edge = jumlah
    kejadian yang menghubungkan wilayah ke kategori tsb.
    """
    G = nx.Graph()

    zone_ids = df["zone_id"].unique()
    G.add_nodes_from(zone_ids, bipartite=0, node_type="wilayah")

    cat_cols = {
        "depth_class": df["depth_class"].astype(str),
        "mag_band": df["mag_band"].astype(str),
    }
    df = df.copy()
    df["tsunami_cat"] = df["tsunami"].map({1: "tsunami_ya", 0: "tsunami_tidak"})
    cat_cols["tsunami_cat"] = df["tsunami_cat"]

    for col_name, series in cat_cols.items():
        for cat_val in series.unique():
            node_name = f"{col_name}:{cat_val}"
            G.add_node(node_name, bipartite=1, node_type="kategori")

    for col_name, series in cat_cols.items():
        edge_counts = df.groupby(["zone_id"])[col_name].value_counts()
        for (zone_id, cat_val), count in edge_counts.items():
            node_name = f"{col_name}:{cat_val}"
            if G.has_edge(zone_id, node_name):
                G[zone_id][node_name]["weight"] += count
            else:
                G.add_edge(zone_id, node_name, weight=int(count))
    return G


def compute_zone_multihazard_degree(G: nx.Graph) -> pd.DataFrame:
    """Degree wilayah di graph bipartite = keragaman karakteristik hazard wilayah itu."""
    wilayah_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "wilayah"]
    rows = []
    for w in wilayah_nodes:
        neighbors = list(G.neighbors(w))
        rows.append(dict(zone_id=w, multihazard_degree=len(neighbors), neighbors=", ".join(neighbors)))
    return pd.DataFrame(rows).sort_values("multihazard_degree", ascending=False)


def project_zone_similarity(G: nx.Graph) -> nx.Graph:
    """Proyeksi wilayah-ke-wilayah: dua wilayah terhubung kalau berbagi >=1 kategori sama."""
    wilayah_nodes = [n for n, d in G.nodes(data=True) if d.get("node_type") == "wilayah"]
    return nx.bipartite.weighted_projected_graph(G, wilayah_nodes)

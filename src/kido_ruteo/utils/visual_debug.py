"""kido_ruteo.utils.visual_debug

Utilidades de visualización para depurar el pipeline en checkpoint 2030.

Este módulo fuerza backend headless (Agg) para evitar dependencia de Tk/Tcl.
"""

from __future__ import annotations

import logging
import os
from typing import Hashable, Optional

import matplotlib

matplotlib.use("Agg")

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

logger = logging.getLogger(__name__)


def _pos(G: nx.Graph, node: Hashable) -> Optional[tuple[float, float]]:
    data = G.nodes.get(node, {})
    if "x" in data and "y" in data:
        return float(data["x"]), float(data["y"])
    p = data.get("pos")
    if isinstance(p, (tuple, list)) and len(p) == 2:
        return float(p[0]), float(p[1])
    return None


class DebugVisualizer:
    def __init__(self, output_dir: str = "plots"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def plot_logic_flow(self, df_trace: pd.DataFrame, save_to: str) -> None:
        rows: list[list[str]] = []
        for _, r in df_trace.iterrows():
            origin = str(r.get("origin_id", ""))
            dest = str(r.get("destination_id", ""))
            od = f"{origin}->{dest}"

            mc = r.get("mc_distance_m")
            mc2 = r.get("mc2_distance_m")
            has_route = pd.notna(mc) and pd.notna(mc2) and float(mc) > 0 and float(mc2) > 0

            cap_total = r.get("cap_total")
            has_cap = pd.notna(cap_total) and float(cap_total) > 0

            cong = r.get("congruence_id")
            cong_ok = pd.notna(cong) and int(cong) != 4

            veh_total = r.get("veh_total")
            veh_ok = pd.notna(veh_total)

            rows.append(
                [
                    od,
                    "OK" if has_route else "NO",
                    str(r.get("sense_code") if pd.notna(r.get("sense_code")) else "NA"),
                    "OK" if has_cap else "NO",
                    str(int(cong)) if pd.notna(cong) else "NA",
                    "OK" if cong_ok else "NO",
                    f"{float(veh_total):.3f}" if veh_ok else "NA",
                ]
            )

        fig, ax = plt.subplots(figsize=(18, max(8, len(rows) * 0.25)))
        col_labels = ["OD", "route", "sense", "cap", "cong_id", "cong_ok", "veh_total"]
        tbl = ax.table(cellText=rows, colLabels=col_labels, cellLoc="center", loc="center")
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        tbl.scale(1.0, 1.4)
        ax.axis("off")
        ax.set_title("Checkpoint 2030 — Flujo lógico (debug)", fontsize=12, fontweight="bold")
        plt.tight_layout()
        plt.savefig(save_to, dpi=180, bbox_inches="tight")
        logger.info("✅ Gráfica de flujo lógico guardada: %s", save_to)
        plt.close()

    def plot_routes_overview(
        self,
        G: nx.Graph,
        checkpoint_node: Hashable,
        routes_mc: list[list[Hashable]],
        routes_mc2: list[list[Hashable]],
        origin_nodes: Optional[list[Hashable]] = None,
        dest_nodes: Optional[list[Hashable]] = None,
        save_to: str = "",
        title: str = "Checkpoint 2030 — Mapa resumen MC (rojo) vs MC2 (azul)",
    ) -> None:
        if not save_to:
            save_to = f"{self.output_dir}/checkpoint2030_routes_overview.png"

        def edges_from_path(p: list[Hashable]) -> list[tuple[Hashable, Hashable]]:
            return [(p[i], p[i + 1]) for i in range(len(p) - 1)] if p and len(p) > 1 else []

        mc_edges: set[tuple[Hashable, Hashable]] = set()
        mc2_edges: set[tuple[Hashable, Hashable]] = set()
        nodes: set[Hashable] = {checkpoint_node}

        for p in routes_mc:
            for e in edges_from_path(p):
                mc_edges.add(e)
                nodes.update(e)
        for p in routes_mc2:
            for e in edges_from_path(p):
                mc2_edges.add(e)
                nodes.update(e)

        if origin_nodes:
            nodes.update(origin_nodes)
        if dest_nodes:
            nodes.update(dest_nodes)

        pos: dict[Hashable, tuple[float, float]] = {}
        for n in nodes:
            p = _pos(G, n)
            if p is not None:
                pos[n] = p

        fig, ax = plt.subplots(figsize=(14, 12))

        if mc2_edges:
            nx.draw_networkx_edges(G, pos, edgelist=list(mc2_edges), ax=ax, edge_color="blue", width=1.8, alpha=0.20)
        if mc_edges:
            nx.draw_networkx_edges(G, pos, edgelist=list(mc_edges), ax=ax, edge_color="red", width=1.8, alpha=0.20)

        if origin_nodes:
            o_in = [n for n in origin_nodes if n in pos]
            if o_in:
                nx.draw_networkx_nodes(G, pos, nodelist=o_in, ax=ax, node_color="green", node_size=10, alpha=0.6)
        if dest_nodes:
            d_in = [n for n in dest_nodes if n in pos]
            if d_in:
                nx.draw_networkx_nodes(G, pos, nodelist=d_in, ax=ax, node_color="black", node_size=10, alpha=0.6)

        if checkpoint_node in pos:
            nx.draw_networkx_nodes(
                G,
                pos,
                nodelist=[checkpoint_node],
                ax=ax,
                node_color="gold",
                node_size=250,
                node_shape="*",
                edgecolors="black",
                linewidths=2,
            )
            ax.annotate("Checkpoint 2030", xy=pos[checkpoint_node], xytext=(10, 10), textcoords="offset points")

        ax.legend(
            handles=[
                mpatches.Patch(color="red", label="MC"),
                mpatches.Patch(color="blue", label="MC2"),
            ],
            loc="upper right",
        )
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.grid(True, alpha=0.2)
        plt.tight_layout()
        plt.savefig(save_to, dpi=220, bbox_inches="tight")
        logger.info("✅ Mapa resumen de rutas guardado: %s", save_to)
        plt.close()

    def plot_routes_overview_map(
        self,
        G: nx.Graph,
        checkpoint_node: Hashable,
        routes_mc: list[list[Hashable]],
        routes_mc2: list[list[Hashable]],
        roads_gdf,
        zones_gdf=None,
        origin_nodes: Optional[list[Hashable]] = None,
        dest_nodes: Optional[list[Hashable]] = None,
        save_to: str = "",
        title: str = "Checkpoint 2030 — Mapa (zonas + carreteras) con rutas MC vs MC2",
    ) -> None:
        """Map-like overview: zones + roads as baselayers + routes overlay.

        `roads_gdf` should be a GeoDataFrame of the road network (LineString).
        `zones_gdf` (optional) should be a GeoDataFrame of zone polygons.

        Both will be reprojected to the graph CRS when possible.
        """
        # Local imports to keep module lightweight
        import geopandas as gpd
        from shapely.geometry import LineString

        if not save_to:
            save_to = f"{self.output_dir}/checkpoint2030_routes_overview_map.png"

        graph_crs = G.graph.get('crs', None)

        roads = roads_gdf
        if hasattr(roads, 'crs') and graph_crs is not None and roads.crs != graph_crs:
            roads = roads.to_crs(graph_crs)

        zones = zones_gdf
        if zones is not None and hasattr(zones, 'crs') and graph_crs is not None and zones.crs != graph_crs:
            zones = zones.to_crs(graph_crs)

        def path_to_linestring(p: list[Hashable]) -> LineString | None:
            coords: list[tuple[float, float]] = []
            for n in p:
                xy = _pos(G, n)
                if xy is None:
                    return None
                coords.append(xy)
            if len(coords) < 2:
                return None
            return LineString(coords)

        mc_lines = [ls for ls in (path_to_linestring(p) for p in routes_mc) if ls is not None]
        mc2_lines = [ls for ls in (path_to_linestring(p) for p in routes_mc2) if ls is not None]

        fig, ax = plt.subplots(figsize=(14, 12))

        # Determine bbox of interest (prefer routes -> roads)
        bounds = None
        if mc_lines or mc2_lines:
            all_lines = mc_lines + mc2_lines
            b = gpd.GeoSeries(all_lines, crs=graph_crs).total_bounds  # (minx,miny,maxx,maxy)
            bounds = tuple(map(float, b))
        elif roads is not None and not roads.empty:
            b = roads.total_bounds
            bounds = tuple(map(float, b))

        def _pad_bbox(b, pad_ratio: float = 0.05, min_pad: float = 50.0):
            minx, miny, maxx, maxy = b
            dx = max(maxx - minx, 0.0)
            dy = max(maxy - miny, 0.0)
            pad_x = max(dx * pad_ratio, min_pad)
            pad_y = max(dy * pad_ratio, min_pad)
            return (minx - pad_x, miny - pad_y, maxx + pad_x, maxy + pad_y)

        bbox = _pad_bbox(bounds) if bounds is not None else None

        # Filter baselayers to bbox (keeps map local)
        if bbox is not None:
            minx, miny, maxx, maxy = bbox
            try:
                from shapely.geometry import box

                clip_poly = box(minx, miny, maxx, maxy)
            except Exception:
                clip_poly = None

            if zones is not None and not zones.empty and clip_poly is not None:
                try:
                    zones = zones[zones.geometry.intersects(clip_poly)].copy()
                except Exception:
                    pass
            if roads is not None and not roads.empty:
                try:
                    # fast bbox filter
                    roads = roads.cx[minx:maxx, miny:maxy]
                except Exception:
                    pass

        # Baselayers
        if zones is not None and not zones.empty:
            zones.plot(ax=ax, facecolor='none', edgecolor='#999999', linewidth=0.6, alpha=0.6)

        if roads is not None and not roads.empty:
            roads.plot(ax=ax, color='#666666', linewidth=0.3, alpha=0.35)

        # Routes overlay
        if mc2_lines:
            gpd.GeoSeries(mc2_lines, crs=graph_crs).plot(ax=ax, color='blue', linewidth=1.8, alpha=0.55)
        if mc_lines:
            gpd.GeoSeries(mc_lines, crs=graph_crs).plot(ax=ax, color='red', linewidth=1.8, alpha=0.55)

        # Key points
        if origin_nodes:
            o_pts = [(_pos(G, n), n) for n in origin_nodes]
            o_xy = [p for p, _ in o_pts if p is not None]
            if o_xy:
                xs, ys = zip(*o_xy)
                ax.scatter(xs, ys, s=8, c='green', alpha=0.7, label='Orígenes')
        if dest_nodes:
            d_pts = [(_pos(G, n), n) for n in dest_nodes]
            d_xy = [p for p, _ in d_pts if p is not None]
            if d_xy:
                xs, ys = zip(*d_xy)
                ax.scatter(xs, ys, s=8, c='black', alpha=0.7, label='Destinos')

        cp_xy = _pos(G, checkpoint_node)
        if cp_xy is not None:
            ax.scatter([cp_xy[0]], [cp_xy[1]], s=220, c='gold', edgecolors='black', marker='*', linewidths=1.5, label='Checkpoint 2030')

        ax.set_title(title, fontsize=12, fontweight='bold')
        if bbox is not None:
            minx, miny, maxx, maxy = bbox
            ax.set_xlim(minx, maxx)
            ax.set_ylim(miny, maxy)

        ax.set_axis_off()
        ax.legend(loc='upper right')
        plt.tight_layout()
        plt.savefig(save_to, dpi=220, bbox_inches='tight')
        logger.info("✅ Mapa tipo GIS guardado: %s", save_to)
        plt.close()

    def plot_route_comparison(
        self,
        G: nx.Graph,
        origin_node: Hashable,
        dest_node: Hashable,
        checkpoint_node: Hashable,
        mc_path: Optional[list[Hashable]],
        mc2_path: Optional[list[Hashable]],
        origin_id: str,
        dest_id: str,
        sense_code: Optional[str] = None,
        save_to: str = "",
    ) -> None:
        """Plot one OD pair: MC (red) vs MC2 (blue)."""
        if not save_to:
            save_to = f"{self.output_dir}/checkpoint2030_route_{origin_id}_{dest_id}.png"

        def edges_from_path(p: Optional[list[Hashable]]) -> list[tuple[Hashable, Hashable]]:
            if not p or len(p) < 2:
                return []
            return [(p[i], p[i + 1]) for i in range(len(p) - 1)]

        mc_edges = edges_from_path(mc_path)
        mc2_edges = edges_from_path(mc2_path)

        nodes: set[Hashable] = {origin_node, dest_node, checkpoint_node}
        for u, v in mc_edges:
            nodes.add(u)
            nodes.add(v)
        for u, v in mc2_edges:
            nodes.add(u)
            nodes.add(v)

        pos: dict[Hashable, tuple[float, float]] = {}
        for n in nodes:
            p = _pos(G, n)
            if p is not None:
                pos[n] = p

        fig, ax = plt.subplots(figsize=(12, 10))

        if mc2_edges:
            nx.draw_networkx_edges(G, pos, edgelist=mc2_edges, ax=ax, edge_color="blue", width=2.2, alpha=0.45)
        if mc_edges:
            nx.draw_networkx_edges(G, pos, edgelist=mc_edges, ax=ax, edge_color="red", width=2.2, alpha=0.45)

        # Nodes
        if origin_node in pos:
            nx.draw_networkx_nodes(G, pos, nodelist=[origin_node], ax=ax, node_color="green", node_size=60, alpha=0.9)
        if dest_node in pos:
            nx.draw_networkx_nodes(G, pos, nodelist=[dest_node], ax=ax, node_color="black", node_size=60, alpha=0.9)
        if checkpoint_node in pos:
            nx.draw_networkx_nodes(
                G,
                pos,
                nodelist=[checkpoint_node],
                ax=ax,
                node_color="gold",
                node_size=240,
                node_shape="*",
                edgecolors="black",
                linewidths=1.5,
            )

        title = f"OD {origin_id}->{dest_id} | sentido={sense_code or 'NA'}"
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.legend(
            handles=[
                mpatches.Patch(color="red", label="MC"),
                mpatches.Patch(color="blue", label="MC2"),
            ],
            loc="upper right",
        )
        ax.grid(True, alpha=0.2)
        plt.tight_layout()
        plt.savefig(save_to, dpi=200, bbox_inches="tight")
        logger.info("✅ Plot OD guardado: %s", save_to)
        plt.close()

    def plot_sense_detail(
        self,
        bearing_in: Optional[float],
        bearing_out: Optional[float],
        cardinality_in: Optional[int],
        cardinality_out: Optional[int],
        sense_code: Optional[str],
        origin_id: str,
        dest_id: str,
        save_to: str = "",
    ) -> None:
        """Panel de texto simple con entradas/salidas del sentido derivado."""
        if not save_to:
            save_to = f"{self.output_dir}/checkpoint2030_sense_{origin_id}_{dest_id}.png"

        fig, ax = plt.subplots(figsize=(8, 4))
        ax.axis("off")

        lines = [
            f"OD: {origin_id} -> {dest_id}",
            f"sense_code: {sense_code or 'NA'}",
            f"bearing_in:  {bearing_in if bearing_in is not None else 'NA'}",
            f"bearing_out: {bearing_out if bearing_out is not None else 'NA'}",
            f"card_in:     {cardinality_in if cardinality_in is not None else 'NA'}",
            f"card_out:    {cardinality_out if cardinality_out is not None else 'NA'}",
        ]
        ax.text(0.02, 0.95, "\n".join(lines), va="top", ha="left", fontsize=11, family="monospace")

        plt.tight_layout()
        plt.savefig(save_to, dpi=200, bbox_inches="tight")
        logger.info("✅ Plot sentido guardado: %s", save_to)
        plt.close()


def visualize_logic_flow(df_trace: pd.DataFrame, output_dir: str = "plots") -> str:
    viz = DebugVisualizer(output_dir)
    out = f"{output_dir}/checkpoint2030_logic_flow.png"
    viz.plot_logic_flow(df_trace, save_to=out)
    return out

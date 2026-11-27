"""Escena navideña animada con Tkinter.

Requisitos: Python 3.10 o superior.
No necesita instalar paquetes externos: utiliza únicamente Tkinter.

Controles:
    ESPACIO  Pausar / continuar
    R        Reiniciar la animación
    F11      Activar / desactivar pantalla completa
    ESC      Salir

Ejecución:
    python arbol_navidad_tkinter.py
"""

from __future__ import annotations

import math
import random
import time
import tkinter as tk
from dataclasses import dataclass


# ---------------------------------------------------------------------------
# Configuración de la escena
# ---------------------------------------------------------------------------
WIDTH = 1000
HEIGHT = 760
FPS_MS = 33                 # aproximadamente 30 fotogramas por segundo
TREE_CENTER_X = 505
TREE_TOP_Y = 166
TREE_BASE_Y = 626
TREE_TIERS = 10
TREE_TIER_INTERVAL = 0.34   # segundos entre niveles del árbol
BUILD_DURATION = TREE_TIERS * TREE_TIER_INTERVAL


@dataclass
class Snowflake:
    item_id: int
    x: float
    y: float
    speed: float
    drift: float
    size: float
    phase: float


class ResponsiveCanvas:
    """Adapta las coordenadas del diseño base al tamaño real de la ventana.

    Mantiene la proporción original para evitar deformaciones. Si la ventana
    cambia de tamaño, escala y centra todos los elementos de la escena.
    """

    SCENE_TAG = "__responsive_scene__"

    def __init__(self, canvas: tk.Canvas, logical_width: int,
                 logical_height: int, actual_width: int,
                 actual_height: int) -> None:
        self.canvas = canvas
        self.logical_width = logical_width
        self.logical_height = logical_height
        self.scale = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.item_metrics: dict[int, dict[str, object]] = {}
        self.resize(actual_width, actual_height, first=True)

    def _map_coords(self, values: object) -> list[float]:
        coords = list(values)  # type: ignore[arg-type]
        mapped: list[float] = []
        for index, value in enumerate(coords):
            number = float(value)
            if index % 2 == 0:
                mapped.append(number * self.scale + self.offset_x)
            else:
                mapped.append(number * self.scale + self.offset_y)
        return mapped

    def _scale_font(self, font: object) -> object:
        if isinstance(font, (tuple, list)) and len(font) >= 2:
            result = list(font)
            try:
                size = int(result[1])
                scaled = max(6, round(abs(size) * self.scale))
                result[1] = -scaled if size < 0 else scaled
                return tuple(result)
            except (TypeError, ValueError):
                return font
        return font

    def _scaled_options(self, options: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
        rendered = dict(options)
        metrics: dict[str, object] = {}
        if "width" in rendered and isinstance(rendered["width"], (int, float)):
            metrics["width"] = rendered["width"]
            rendered["width"] = max(1, float(rendered["width"]) * self.scale)
        if "font" in rendered:
            metrics["font"] = rendered["font"]
            rendered["font"] = self._scale_font(rendered["font"])
        return rendered, metrics

    def _create(self, method: str, *args: object, **kwargs: object) -> int:
        if args and isinstance(args[0], (tuple, list)):
            mapped_args = (self._map_coords(args[0]), *args[1:])
        else:
            mapped_args = tuple(self._map_coords(args))

        options = dict(kwargs)
        tags = options.get("tags", ())
        if isinstance(tags, str):
            tags = (tags,)
        else:
            tags = tuple(tags) if tags else ()
        options["tags"] = (*tags, self.SCENE_TAG)

        rendered_options, metrics = self._scaled_options(options)
        item_id = getattr(self.canvas, method)(*mapped_args, **rendered_options)
        if metrics:
            self.item_metrics[item_id] = metrics
        return item_id

    def __getattr__(self, name: str):
        if name.startswith("create_"):
            return lambda *args, **kwargs: self._create(name, *args, **kwargs)
        return getattr(self.canvas, name)

    def coords(self, item: int, *coords: float):
        if coords:
            return self.canvas.coords(item, *self._map_coords(coords))
        return self.canvas.coords(item)

    def move(self, item: object, dx: float, dy: float) -> None:
        self.canvas.move(item, dx * self.scale, dy * self.scale)

    def resize(self, actual_width: int, actual_height: int,
               first: bool = False) -> None:
        if actual_width < 2 or actual_height < 2:
            return
        new_scale = min(
            actual_width / self.logical_width,
            actual_height / self.logical_height,
        )
        new_offset_x = (actual_width - self.logical_width * new_scale) / 2
        new_offset_y = (actual_height - self.logical_height * new_scale) / 2

        if not first:
            factor = new_scale / self.scale
            self.canvas.scale(self.SCENE_TAG, 0, 0, factor, factor)
            self.canvas.move(
                self.SCENE_TAG,
                new_offset_x - self.offset_x * factor,
                new_offset_y - self.offset_y * factor,
            )

        self.scale = new_scale
        self.offset_x = new_offset_x
        self.offset_y = new_offset_y

        if not first:
            for item_id, metrics in self.item_metrics.items():
                config: dict[str, object] = {}
                if "width" in metrics:
                    config["width"] = max(1, float(metrics["width"]) * self.scale)
                if "font" in metrics:
                    config["font"] = self._scale_font(metrics["font"])
                if config:
                    try:
                        self.canvas.itemconfig(item_id, **config)
                    except tk.TclError:
                        pass


class ChristmasScene:
    """Dibuja y anima una escena navideña en un Canvas de Tkinter."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Una Navidad mágica | Python + Tkinter")
        self.root.configure(bg="#071426")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(1100, max(850, screen_width - 80))
        window_height = min(840, max(620, screen_height - 100))
        pos_x = max(0, (screen_width - window_width) // 2)
        pos_y = max(0, (screen_height - window_height) // 2)
        self.root.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
        self.root.resizable(True, True)
        self.root.attributes("-fullscreen", True)

        # El Canvas ocupa toda la pantalla. La escena conserva su proporción
        # y se centra automáticamente en monitores de distintos tamaños.
        self.raw_canvas = tk.Canvas(
            root, bg="#071426", highlightthickness=0, bd=0,
        )
        self.raw_canvas.pack(fill=tk.BOTH, expand=True)
        self.root.update_idletasks()
        actual_width = max(WIDTH, self.raw_canvas.winfo_width())
        actual_height = max(HEIGHT, self.raw_canvas.winfo_height())
        self.viewport = ResponsiveCanvas(
            self.raw_canvas, WIDTH, HEIGHT, actual_width, actual_height,
        )
        self.canvas = self.viewport

        self.rng = random.Random(27)
        self.paused = False
        self.started_at = time.perf_counter()
        self.paused_total = 0.0
        self.pause_started: float | None = None
        self.elapsed = 0.0
        self.built_tiers = 0
        self.garland_segments = 0
        self.light_items: list[tuple[int, float, str]] = []
        self.gifts: list[dict[str, float | str | bool]] = []
        self.snowflakes: list[Snowflake] = []
        self.twinkle_stars: list[tuple[int, float]] = []
        self.santa_last_direction = 1

        self._draw_viewport_background(actual_width, actual_height)
        self._draw_background()
        self._draw_ground()
        self._draw_viewport_controls()
        self._prepare_snow()
        self._prepare_tree_decorations()

        self.root.bind("<space>", self.toggle_pause)
        self.root.bind("<Escape>", lambda _event: self.root.destroy())
        self.root.bind("<t>", self.toggle_fullscreen)
        self.root.bind("r", self.restart)
        self.root.bind("R", self.restart)
        self.raw_canvas.bind("<Configure>", self._on_canvas_configure)
        self.root.after(100, self.animate)

    # ------------------------------------------------------------------
    # Fondo
    # ------------------------------------------------------------------
    @staticmethod
    def _mix_color(a: str, b: str, amount: float) -> str:
        """Interpola dos colores hexadecimales."""
        amount = max(0.0, min(1.0, amount))
        a_rgb = tuple(int(a[i:i + 2], 16) for i in (1, 3, 5))
        b_rgb = tuple(int(b[i:i + 2], 16) for i in (1, 3, 5))
        result = tuple(round(x + (y - x) * amount) for x, y in zip(a_rgb, b_rgb))
        return "#" + "".join(f"{component:02x}" for component in result)

    def _draw_viewport_background(self, width: int, height: int) -> None:
        """Pinta el cielo y las montañas lejanas a lo ancho de toda la pantalla."""
        self.raw_canvas.delete("viewport_bg")
        top, bottom = "#061021", "#17385a"
        bands = max(90, min(180, height // 7))
        for index in range(bands):
            y1 = index * height / bands
            y2 = (index + 1) * height / bands + 1
            color = self._mix_color(top, bottom, index / max(1, bands - 1))
            self.raw_canvas.create_rectangle(
                0, y1, width, y2, fill=color, outline="", tags="viewport_bg",
            )

        # Cordillera lejana de borde a borde: evita que los laterales queden vacíos
        # en monitores panorámicos. La escena principal se dibuja encima de ella.
        far_ridge = [
            0, height * 0.75,
            width * 0.10, height * 0.61,
            width * 0.20, height * 0.73,
            width * 0.34, height * 0.59,
            width * 0.48, height * 0.75,
            width * 0.62, height * 0.62,
            width * 0.77, height * 0.74,
            width * 0.90, height * 0.60,
            width, height * 0.73,
            width, height, 0, height,
        ]
        self.raw_canvas.create_polygon(
            *far_ridge, fill="#102941", outline="", tags="viewport_bg",
        )
        near_ridge = [
            0, height * 0.80,
            width * 0.13, height * 0.69,
            width * 0.25, height * 0.79,
            width * 0.39, height * 0.66,
            width * 0.54, height * 0.80,
            width * 0.69, height * 0.68,
            width * 0.83, height * 0.79,
            width, height * 0.68,
            width, height, 0, height,
        ]
        self.raw_canvas.create_polygon(
            *near_ridge, fill="#173653", outline="", tags="viewport_bg",
        )

        # Estrellas adicionales en los márgenes de pantallas panorámicas.
        for _ in range(max(45, width // 24)):
            x = self.rng.uniform(0, width)
            y = self.rng.uniform(10, height * 0.68)
            radius = self.rng.choice((0.7, 1.0, 1.3, 1.6))
            shade = self.rng.choice(("#526b88", "#718aa5", "#a0b4c8"))
            self.raw_canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                fill=shade, outline="", tags="viewport_bg",
            )
        self.raw_canvas.tag_lower("viewport_bg")

    def _on_canvas_configure(self, event: tk.Event) -> None:
        width = int(getattr(event, "width", WIDTH))
        height = int(getattr(event, "height", HEIGHT))
        if width < 2 or height < 2:
            return
        self.viewport.resize(width, height)
        self._draw_viewport_background(width, height)
        self._draw_ground()
        self._draw_viewport_controls()

    def toggle_fullscreen(self, _event: object = None) -> None:
        current = bool(self.root.attributes("-fullscreen"))
        self.root.attributes("-fullscreen", not current)

    def _draw_viewport_controls(self) -> None:
        """Mantiene las instrucciones fuera de la trayectoria de Papá Noel."""
        self.raw_canvas.delete("viewport_controls")
        width = max(1, self.raw_canvas.winfo_width())
        height = max(1, self.raw_canvas.winfo_height())
        self.raw_canvas.create_text(
            width / 2,
            height * 0.978,
            text="ESPACIO: PAUSA   •   R: REINICIAR   •   t: PANTALLA COMPLETA   •   ESC: SALIR",
            fill="#71899a",
            font=("Arial", max(9, round(height * 0.011))),
            anchor="center",
            tags="viewport_controls",
        )

    def _draw_background(self) -> None:
        # El degradado ocupa toda la pantalla y se dibuja por separado.
        # Los elementos siguientes pertenecen al área proporcional de la escena.
        # Resplandor lunar suave.
        self.canvas.create_oval(
            760, 63, 884, 187, fill="#142b46", outline="", tags="background"
        )
        self.canvas.create_oval(
            779, 73, 865, 159, fill="#f6edcf", outline="#fff8e8", width=1,
            tags="background",
        )
        self.canvas.create_oval(
            800, 94, 817, 111, fill="#e5dfc9", outline="", tags="background"
        )
        self.canvas.create_oval(
            838, 119, 848, 129, fill="#e5dfc9", outline="", tags="background"
        )

        # Estrellas del cielo.
        for _ in range(105):
            x = self.rng.uniform(18, WIDTH - 18)
            y = self.rng.uniform(22, 440)
            size = self.rng.choice((1.0, 1.3, 1.7, 2.0))
            color = self.rng.choice(("#8daac5", "#b6c9dc", "#f4e8c6", "#7396b7"))
            item = self.canvas.create_oval(
                x - size, y - size, x + size, y + size,
                fill=color, outline="", tags="background",
            )
            self.twinkle_stars.append((item, self.rng.uniform(0, math.tau)))

        # Pequeñas cruces luminosas en el cielo.
        for x, y in ((120, 120), (300, 82), (690, 220), (915, 280), (840, 360)):
            self.canvas.create_line(x - 4, y, x + 4, y, fill="#8faec8", width=1, tags="background")
            self.canvas.create_line(x, y - 4, x, y + 4, fill="#8faec8", width=1, tags="background")

        # Pinos lejanos, en silueta.
        for x, scale in ((72, 0.72), (174, 0.55), (840, 0.72), (930, 0.88)):
            self._draw_distant_pine(x, 570, scale)

        self.canvas.create_text(
            WIDTH / 2, 34, text="UNA NAVIDAD MÁGICA",
            fill="#d8e6ee", font=("Georgia", 17, "bold"),
            tags="background",
        )
        self.canvas.create_text(
            WIDTH / 2, 59, text="una pequeña escena hecha con Python",
            fill="#829eb5", font=("Georgia", 9, "italic"),
            tags="background",
        ) 
        self.canvas.create_text(
            WIDTH / 1, 34, text="Programación I",
            fill="#829eb5", font=("Georgia", 12, "bold"),
            tags="background",
        )

    def _draw_distant_pine(self, x: float, base_y: float, scale: float) -> None:
        height = 118 * scale
        width = 48 * scale
        self.canvas.create_polygon(
            x, base_y - height,
            x - width * 0.52, base_y - height * 0.42,
            x - width * 0.25, base_y - height * 0.43,
            x - width, base_y,
            x + width, base_y,
            x + width * 0.25, base_y - height * 0.43,
            x + width * 0.52, base_y - height * 0.42,
            fill="#102d36", outline="", tags="background",
        )

    def _draw_ground(self) -> None:
        """Dibuja un campo de nieve continuo que cubre todo el ancho visible.

        Se dibuja en coordenadas reales del Canvas, no en las coordenadas
        lógicas de la escena, para que también cubra los márgenes panorámicos.
        """
        self.raw_canvas.delete("ground_fixed")
        width = max(1, self.raw_canvas.winfo_width())
        height = max(1, self.raw_canvas.winfo_height())

        # Borde superior ligeramente ondulado, como una loma de nieve natural.
        ridge: list[float] = []
        steps = 40
        for index in range(steps + 1):
            x = width * index / steps
            position = index / steps
            center_lift = 1.0 - abs(position - 0.5) * 2.0
            small_wave = math.sin(position * math.tau * 2.0) * 0.004
            y = height * (0.866 - 0.034 * center_lift + small_wave)
            ridge.extend((x, y))

        snow_polygon = [*ridge, width, height, 0, height]
        self.raw_canvas.create_polygon(
            *snow_polygon, fill="#e8f0f1", outline="", tags="ground_fixed",
        )
        self.raw_canvas.create_line(
            *ridge, fill="#f7fbfa", width=max(2, height * 0.004),
            smooth=True, splinesteps=18, tags="ground_fixed",
        )

        # Una segunda ondulación muy suave en primer plano para dar profundidad.
        foreground = [
            0, height * 0.955,
            width * 0.16, height * 0.939,
            width * 0.34, height * 0.952,
            width * 0.52, height * 0.932,
            width * 0.71, height * 0.951,
            width * 0.88, height * 0.938,
            width, height * 0.950,
            width, height, 0, height,
        ]
        self.raw_canvas.create_polygon(
            *foreground, fill="#f0f5f4", outline="", tags="ground_fixed",
        )

        # Destellos distribuidos por toda la superficie, no solo bajo el árbol.
        for _ in range(max(70, width // 18)):
            x = self.rng.uniform(0, width)
            y = self.rng.uniform(height * 0.875, height * 0.99)
            radius = self.rng.choice((0.7, 0.9, 1.1, 1.3))
            color = self.rng.choice(("#c4d5d9", "#d3e0e2", "#ffffff"))
            self.raw_canvas.create_oval(
                x - radius, y - radius, x + radius, y + radius,
                fill=color, outline="", tags="ground_fixed",
            )

        # En un redimensionamiento, coloca el piso sobre el paisaje pero detrás
        # de los copos, el árbol y los regalos.
        if self.raw_canvas.find_withtag("snow"):
            self.raw_canvas.tag_lower("ground_fixed", "snow")
        elif self.raw_canvas.find_withtag("tree"):
            self.raw_canvas.tag_lower("ground_fixed", "tree")

    # ------------------------------------------------------------------
    # Árbol: construcción por niveles
    # ------------------------------------------------------------------
    def _tier_geometry(self, index: int) -> tuple[list[float], float, float, float]:
        cx = TREE_CENTER_X
        top_y = TREE_TOP_Y + index * 45
        bottom_y = top_y + 82
        half_width = 27 + index * 16.1

        points = [
            cx, top_y,
            cx - half_width * 0.48, top_y + 24,
            cx - half_width * 0.35, top_y + 27,
            cx - half_width, bottom_y - 10,
            cx - half_width * 0.70, bottom_y - 8,
            cx - half_width * 0.76, bottom_y,
            cx, bottom_y - 17,
            cx + half_width * 0.76, bottom_y,
            cx + half_width * 0.70, bottom_y - 8,
            cx + half_width, bottom_y - 10,
            cx + half_width * 0.35, top_y + 27,
            cx + half_width * 0.48, top_y + 24,
        ]
        return points, top_y, bottom_y, half_width

    def _draw_tree_tier(self, index: int) -> None:
        points, top_y, bottom_y, half_width = self._tier_geometry(index)
        greens = ("#14583d", "#176745", "#1a7048", "#176342")
        fill = greens[index % len(greens)]
        self.canvas.create_polygon(
            points, fill=fill, outline="#2b8a5b", width=2,
            joinstyle=tk.ROUND, tags="tree",
        )

        # Vetas cortas que sugieren ramas y nieve acumulada.
        for branch in range(3):
            y = top_y + 31 + branch * 15
            spread = half_width * (0.34 + branch * 0.20)
            self.canvas.create_line(
                TREE_CENTER_X - 5, y,
                TREE_CENTER_X - spread, y + 9,
                fill="#3b9664", width=2, capstyle=tk.ROUND, tags="tree",
            )
            self.canvas.create_line(
                TREE_CENTER_X + 5, y,
                TREE_CENTER_X + spread, y + 9,
                fill="#3b9664", width=2, capstyle=tk.ROUND, tags="tree",
            )

        # Algunas puntas verde claro para dar profundidad.
        for side in (-1, 1):
            self.canvas.create_line(
                TREE_CENTER_X, top_y + 12,
                TREE_CENTER_X + side * half_width * 0.48, top_y + 31,
                fill="#4aa36f", width=2, tags="tree",
            )

        # Un tronco pequeño empieza a verse al construir los niveles inferiores.
        if index == TREE_TIERS - 1:
            self.canvas.create_rectangle(
                TREE_CENTER_X - 22, 590, TREE_CENTER_X + 22, 660,
                fill="#70452f", outline="#8b5b3b", width=2, tags="tree",
            )
            self.canvas.create_line(
                TREE_CENTER_X - 8, 603, TREE_CENTER_X - 8, 648,
                fill="#9a6b43", width=2, tags="tree",
            )

    # ------------------------------------------------------------------
    # Guirnalda y luces
    # ------------------------------------------------------------------
    def _prepare_tree_decorations(self) -> None:
        self.garland_points: list[tuple[float, float]] = []
        start_y = TREE_TOP_Y + 48
        end_y = TREE_BASE_Y - 22
        count = 116
        for index in range(count):
            t = index / (count - 1)
            y = start_y + t * (end_y - start_y)
            half_width = 25 + t * 145
            x = TREE_CENTER_X + math.sin(t * math.tau * 5.2) * half_width * 0.78
            self.garland_points.append((x, y))

        self.light_positions: list[tuple[float, float]] = []
        for index in range(5, count - 3, 5):
            self.light_positions.append(self.garland_points[index])

    def _add_garland_segment(self) -> None:
        if self.garland_segments >= len(self.garland_points) - 1:
            return
        x1, y1 = self.garland_points[self.garland_segments]
        x2, y2 = self.garland_points[self.garland_segments + 1]
        self.canvas.create_line(
            x1, y1, x2, y2, fill="#b99348", width=2,
            capstyle=tk.ROUND, tags="garland",
        )
        self.garland_segments += 1

    def _add_light(self, x: float, y: float, index: int) -> None:
        colors = ("#ff5364", "#ffd166", "#67c8ff", "#f8e7a1", "#c49aff")
        color = colors[index % len(colors)]
        glow = self.canvas.create_oval(
            x - 8, y - 8, x + 8, y + 8,
            fill="#24513e", outline="", tags="lights",
        )
        bulb = self.canvas.create_oval(
            x - 3.2, y - 3.2, x + 3.2, y + 3.2,
            fill=color, outline="#fff2cf", width=1, tags="lights",
        )
        self.light_items.append((bulb, index * 0.67, color))
        # El halo se conserva tenue; el brillo principal cambia en cada fotograma.
        self.canvas.tag_lower(glow, "lights")

    # ------------------------------------------------------------------
    # Estrella
    # ------------------------------------------------------------------
    @staticmethod
    def _star_points(cx: float, cy: float, outer: float, inner: float) -> list[float]:
        points: list[float] = []
        for index in range(10):
            radius = outer if index % 2 == 0 else inner
            angle = -math.pi / 2 + index * math.pi / 5
            points.extend((cx + math.cos(angle) * radius, cy + math.sin(angle) * radius))
        return points

    def _draw_top_star(self, now: float) -> None:
        self.canvas.delete("top_star")
        pulse = 1 + 0.10 * math.sin(now * 3.0)
        cx, cy = TREE_CENTER_X, TREE_TOP_Y - 13
        self.canvas.create_oval(
            cx - 31 * pulse, cy - 31 * pulse,
            cx + 31 * pulse, cy + 31 * pulse,
            fill="#705c2d", outline="", tags="top_star",
        )
        self.canvas.create_oval(
            cx - 20 * pulse, cy - 20 * pulse,
            cx + 20 * pulse, cy + 20 * pulse,
            fill="#b18b37", outline="", tags="top_star",
        )
        self.canvas.create_polygon(
            self._star_points(cx, cy, 22 * pulse, 9 * pulse),
            fill="#ffe58a", outline="#fff7d5", width=2, tags="top_star",
        )
        self.canvas.create_oval(
            cx - 3, cy - 3, cx + 3, cy + 3,
            fill="#ffffff", outline="", tags="top_star",
        )

    # ------------------------------------------------------------------
    # Regalos
    # ------------------------------------------------------------------
    def _create_gift(self, x: float, target_y: float, width: float, height: float,
                     body: str, ribbon: str, name: str) -> None:
        tag = name
        y = target_y + 100
        x2 = x + width
        self.canvas.create_rectangle(
            x, y, x2, y + height, fill=body, outline="#f3d99c", width=2,
            tags=("gift", tag),
        )
        self.canvas.create_rectangle(
            x + width * 0.43, y, x + width * 0.57, y + height,
            fill=ribbon, outline="", tags=("gift", tag),
        )
        self.canvas.create_rectangle(
            x, y + height * 0.40, x2, y + height * 0.52,
            fill=ribbon, outline="", tags=("gift", tag),
        )
        self.canvas.create_oval(
            x + width * 0.28, y - 13, x + width * 0.53, y + 5,
            outline=ribbon, width=4, tags=("gift", tag),
        )
        self.canvas.create_oval(
            x + width * 0.47, y - 13, x + width * 0.72, y + 5,
            outline=ribbon, width=4, tags=("gift", tag),
        )
        self.gifts.append({
            "tag": tag,
            "target_y": target_y,
            "current_y": y,
            "height": height,
            "created_at": self.elapsed,
        })

    def _update_gifts(self) -> None:
        gift_specs = (
            (373, 612, 69, 53, "#b82f49", "#f5d278"),
            (447, 625, 83, 61, "#245c9a", "#f3df9d"),
            (535, 614, 67, 52, "#d28a31", "#fff0bc"),
            (606, 626, 55, 43, "#7e3d83", "#f0c7e9"),
        )
        gifts_start = BUILD_DURATION + 0.65
        for index, spec in enumerate(gift_specs):
            appear_at = gifts_start + index * 0.48
            if self.elapsed >= appear_at and len(self.gifts) <= index:
                x, y, w, h, body, ribbon = spec
                self._create_gift(x, y, w, h, body, ribbon, f"gift_{index}")

        for gift in self.gifts:
            age = max(0.0, self.elapsed - float(gift["created_at"]))
            # Rebote amortiguado al aterrizar.
            offset = 82 * math.exp(-4.2 * age) * abs(math.cos(age * 8.0))
            desired_y = float(gift["target_y"]) + offset
            delta = desired_y - float(gift["current_y"])
            if abs(delta) > 0.05:
                self.canvas.move(str(gift["tag"]), 0, delta)
                gift["current_y"] = desired_y

    # ------------------------------------------------------------------
    # Papá Noel y su trineo
    # ------------------------------------------------------------------
    def _draw_santa(self, anchor_x: float, y: float, direction: int) -> None:
        """Dibuja el trineo; direction=1 vuela a la derecha, -1 a la izquierda."""
        self.canvas.delete("santa")

        def tx(local_x: float) -> float:
            return anchor_x + direction * local_x

        def line(points: tuple[float, ...], color: str, width: int = 2,
                 smooth: bool = False) -> None:
            transformed: list[float] = []
            for i in range(0, len(points), 2):
                transformed.extend((tx(points[i]), y + points[i + 1]))
            self.canvas.create_line(
                *transformed, fill=color, width=width, smooth=smooth,
                capstyle=tk.ROUND, joinstyle=tk.ROUND, tags="santa",
            )

        def oval(x1: float, y1: float, x2: float, y2: float,
                 fill: str, outline: str = "", width: int = 1) -> None:
            xa, xb = tx(x1), tx(x2)
            self.canvas.create_oval(
                min(xa, xb), y + y1, max(xa, xb), y + y2,
                fill=fill, outline=outline, width=width, tags="santa",
            )

        def polygon(points: tuple[float, ...], fill: str, outline: str = "",
                    width: int = 1) -> None:
            transformed: list[float] = []
            for i in range(0, len(points), 2):
                transformed.extend((tx(points[i]), y + points[i + 1]))
            self.canvas.create_polygon(
                *transformed, fill=fill, outline=outline, width=width,
                joinstyle=tk.ROUND, tags="santa",
            )

        # Estela de pequeñas estrellas.
        for index, offset in enumerate((190, 215, 240)):
            sx = tx(-offset * 0.42)
            sparkle_offsets = (-8, 2, 10)
            sy = y + sparkle_offsets[(int(self.elapsed * 3) + index) % 3]
            self.canvas.create_text(
                sx, sy, text="✦", fill="#f6d987",
                font=("Arial", 9), tags="santa",
            )

        # Arnés.
        line((40, 8, 83, 4, 108, 3), "#d6b46d", 2)

        # Reno principal: cuerpo, cuello, cabeza, patas y astas.
        oval(105, -3, 139, 14, "#9a6847", "#d0a477", 1)
        line((112, 10, 108, 24, 106, 27), "#9a6847", 3)
        line((132, 10, 135, 23, 138, 25), "#9a6847", 3)
        line((124, 0, 137, -12, 145, -13), "#9a6847", 5)
        oval(137, -22, 154, -7, "#a97850", "#dfb88a", 1)
        oval(149, -17, 154, -12, "#e94c55")
        oval(141, -18, 144, -15, "#241c20")
        line((143, -21, 139, -34, 134, -39), "#e4d1a9", 2)
        line((140, -28, 147, -35, 151, -41), "#e4d1a9", 2)
        line((151, -35, 155, -36), "#e4d1a9", 2)
        line((136, -34, 131, -34), "#e4d1a9", 2)

        # Segundo reno, más pequeño y ligeramente detrás.
        oval(163, 4, 190, 17, "#80563e", "#c79a72", 1)
        line((170, 14, 169, 25, 166, 27), "#80563e", 3)
        line((185, 14, 187, 24, 190, 26), "#80563e", 3)
        line((180, 6, 190, -4, 197, -5), "#80563e", 4)
        oval(190, -12, 202, -1, "#966b4d", "#c79a72", 1)
        oval(199, -8, 203, -4, "#e94c55")
        line((195, -11, 193, -21, 189, -25), "#e4d1a9", 2)
        line((194, -18, 201, -23, 204, -28), "#e4d1a9", 2)

        # Trineo rojo y patín dorado.
        polygon((-18, 9, 34, 9, 54, 0, 49, 18, 28, 26, -8, 22),
                "#b9273d", "#f1c66e", 2)
        line((-17, 23, 2, 29, 37, 29, 56, 20), "#f4d17c", 3, True)
        line((-12, 8, -18, 17, -29, 19), "#f4d17c", 2)

        # Saco de regalos en el trineo.
        oval(0, -6, 26, 11, "#356e56", "#b5d4a7", 1)
        oval(5, -14, 20, -3, "#4d8968", "#b5d4a7", 1)
        line((9, -8, 18, -8), "#e8c975", 2)

        # Papá Noel sentado.
        polygon((9, -4, 34, -4, 40, 12, 13, 12), "#c72f43", "#efb5a4", 1)
        oval(16, -29, 39, -8, "#f1c49a", "#e7a97c", 1)
        polygon((14, -19, 22, -8, 39, -12, 34, -23), "#fff7e8", "#e3e4df", 1)
        oval(20, -23, 23, -20, "#34272a")
        oval(31, -23, 34, -20, "#34272a")
        oval(26, -17, 31, -12, "#d98d77")
        polygon((13, -27, 18, -42, 39, -39, 43, -27), "#c92e43", "#f3b7a0", 1)
        polygon((14, -28, 25, -34, 39, -29, 41, -25), "#fff4e8", "#fff4e8", 1)
        oval(37, -43, 45, -35, "#fff6eb")
        line((17, 7, 37, 7), "#f2d47c", 2)

    # ------------------------------------------------------------------
    # Nieve y controles
    # ------------------------------------------------------------------
    def _prepare_snow(self) -> None:
        self.snowflakes.clear()
        for _ in range(100):
            x = self.rng.uniform(0, WIDTH)
            y = self.rng.uniform(0, HEIGHT)
            size = self.rng.uniform(1.0, 2.5)
            speed = self.rng.uniform(0.7, 2.1)
            drift = self.rng.uniform(-0.35, 0.35)
            phase = self.rng.uniform(0, math.tau)
            item = self.canvas.create_oval(
                x - size, y - size, x + size, y + size,
                fill="#e4f0f5", outline="", tags="snow",
            )
            self.snowflakes.append(Snowflake(item, x, y, speed, drift, size, phase))

    def _update_snow(self, now: float) -> None:
        for flake in self.snowflakes:
            flake.y += flake.speed
            flake.x += flake.drift + math.sin(now * 1.2 + flake.phase) * 0.25
            if flake.y > HEIGHT + 5:
                flake.y = -5
                flake.x = self.rng.uniform(0, WIDTH)
            if flake.x < -5:
                flake.x = WIDTH + 5
            elif flake.x > WIDTH + 5:
                flake.x = -5
            self.canvas.coords(
                flake.item_id,
                flake.x - flake.size, flake.y - flake.size,
                flake.x + flake.size, flake.y + flake.size,
            )

    def _update_twinkle(self, now: float) -> None:
        for item, phase in self.twinkle_stars:
            brightness = 0.5 + 0.5 * math.sin(now * 2.1 + phase)
            if brightness > 0.78:
                color = "#f8eac4"
            elif brightness > 0.42:
                color = "#9bb6cf"
            else:
                color = "#526f91"
            self.canvas.itemconfig(item, fill=color)

    def _update_lights(self, now: float) -> None:
        for bulb, phase, original_color in self.light_items:
            pulse = 0.5 + 0.5 * math.sin(now * 4.3 + phase)
            if pulse > 0.62:
                color = original_color
            else:
                color = "#8b8d83"
            self.canvas.itemconfig(bulb, fill=color)

    def toggle_pause(self, _event: object = None) -> None:
        if not self.paused:
            self.paused = True
            self.pause_started = time.perf_counter()
        else:
            self.paused = False
            if self.pause_started is not None:
                self.paused_total += time.perf_counter() - self.pause_started
            self.pause_started = None

    def restart(self, _event: object = None) -> None:
        self.canvas.delete("tree")
        self.canvas.delete("garland")
        self.canvas.delete("lights")
        self.canvas.delete("top_star")
        self.canvas.delete("gift")
        self.canvas.delete("santa")
        self.built_tiers = 0
        self.garland_segments = 0
        self.light_items.clear()
        self.gifts.clear()
        self.elapsed = 0.0
        self.started_at = time.perf_counter()
        self.paused_total = 0.0
        self.paused = False
        self.pause_started = None

    # ------------------------------------------------------------------
    # Bucle principal
    # ------------------------------------------------------------------
    def _draw_progress_text(self) -> None:
        self.canvas.delete("progress_text")
        if self.built_tiers < TREE_TIERS:
            message = "Construyendo el árbol..."
        elif not self.gifts:
            message = "Encendiendo la magia de la Navidad..."
        else:
            message = "¡Feliz Navidad!"
        self.canvas.create_text(
            WIDTH / 2, 713, text=message,
            fill="#648094", font=("Georgia", 10, "italic"),
            tags="progress_text",
        )

    def animate(self) -> None:
        if not self.paused:
            current = time.perf_counter()
            self.elapsed = current - self.started_at - self.paused_total
            now = self.elapsed

            # Construcción del árbol, un nivel a la vez.
            wanted_tiers = min(
                TREE_TIERS,
                int(now / TREE_TIER_INTERVAL) + 1,
            )
            while self.built_tiers < wanted_tiers:
                self._draw_tree_tier(self.built_tiers)
                self.built_tiers += 1

            # La guirnalda aparece después de que el árbol queda construido.
            garland_start = BUILD_DURATION + 0.10
            if now >= garland_start:
                wanted_segments = min(
                    len(self.garland_points) - 1,
                    int((now - garland_start) * 58),
                )
                while self.garland_segments < wanted_segments:
                    self._add_garland_segment()

                # Las luces se van colocando a medida que avanza la guirnalda.
                visible_lights = min(
                    len(self.light_positions),
                    int((now - garland_start) * 9),
                )
                while len(self.light_items) < visible_lights:
                    index = len(self.light_items)
                    x, y = self.light_positions[index]
                    self._add_light(x, y, index)

            if now >= BUILD_DURATION + 0.15:
                self._draw_top_star(now)

            self._update_gifts()
            self._update_snow(now)
            self._update_twinkle(now)
            self._update_lights(now)

            # Santa cruza el cielo aproximadamente cada 10 segundos.
            pass_duration = 4.8
            cycle_duration = 10.5
            cycle_position = now % cycle_duration
            if cycle_position < pass_duration:
                pass_number = int(now // cycle_duration)
                direction = 1 if pass_number % 2 == 0 else -1
                progress = cycle_position / pass_duration
                if direction == 1:
                    x = -210 + progress * (WIDTH + 420)
                else:
                    x = WIDTH + 210 - progress * (WIDTH + 420)
                santa_y = 112 + math.sin(now * 2.5) * 8
                self._draw_santa(x, santa_y, direction)
            else:
                self.canvas.delete("santa")

            self._draw_progress_text()

        self.root.after(FPS_MS, self.animate)


def main() -> None:
    root = tk.Tk()
    ChristmasScene(root)
    root.mainloop()


if __name__ == "__main__":
    main()

"""
Solubility analysis tab component.

Mirrors the structure of PlotArea: shows one of three CO2 solubility figures
(pressure, accumulation, saturation) at a time. A compact tab-switcher bar
at the top lets the user pick which graph to display. The matplotlib toolbar
and mouse wheel zoom / right-click pan are wired exactly as in PlotArea.
"""

import logging
import time

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # type: ignore[attr-defined]
from matplotlib.backends.backend_tkagg import NavigationToolbar2Tk  # type: ignore[attr-defined]

from visualize_app.core import AppState
from visualize_app.core import EventBus
from visualize_app.ui.components.base_component import BaseComponent
from visualize_app.ui.theme import COLORS

logger = logging.getLogger(__name__)

# Internal IDs and human-readable labels for the three solubility plots
_SOL_PLOTS = [
    ("pressure", "Давление"),
    ("accumulation", "Накопление CO₂"),
    ("saturation", "Насыщение"),
]


class SolubilityTab(BaseComponent):
    """
    Tab showing individual CO2 solubility figures with a plot-switcher bar.

    Layout (top → bottom):
      ┌──────────────────────────────────┐
      │  [Давление] [Накопление] [Насыщ] │  ← compact tab switcher
      ├──────────────────────────────────┤
      │                                  │
      │        matplotlib canvas         │
      │                                  │
      ├──────────────────────────────────┤
      │  mpl toolbar  |  zoom controls   │  ← toolbar strip (same as PlotArea)
      └──────────────────────────────────┘
    """

    def __init__(self, parent, app_state: AppState, event_bus: EventBus):
        super().__init__(parent, app_state, event_bus)

        # Root frame returned by build()
        self.root_frame: ctk.CTkFrame | None = None

        # Tab-switcher bar references
        self.tab_bar: ctk.CTkFrame | None = None
        self.tab_buttons: dict[str, ctk.CTkButton] = {}

        # Canvas area
        self.canvas_frame: ctk.CTkFrame | None = None
        self.placeholder: ctk.CTkLabel | None = None

        # Current matplotlib canvas / toolbar
        self.current_canvas: FigureCanvasTkAgg | None = None
        self.current_toolbar = None
        self.toolbar_container: ctk.CTkFrame | None = None
        self.zoom_controls: dict = {}

        # Pan state (identical to PlotArea)
        self.pan_state = {
            "active": False,
            "start_x": 0,
            "start_y": 0,
            "last_update": 0,
            "pending_update": None,
            "accumulated_dx": 0,
            "accumulated_dy": 0,
        }

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> ctk.CTkFrame:
        self.root_frame = ctk.CTkFrame(
            self.parent,
            corner_radius=12,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["border"],
        )

        # ── Canvas area ───────────────────────────────────────────────
        self.canvas_frame = ctk.CTkFrame(
            self.root_frame,
            fg_color=COLORS["bg_card"],
            corner_radius=12,
        )
        self.canvas_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Placeholder shown before first calculation
        self.placeholder = ctk.CTkLabel(
            self.canvas_frame,
            text=(
                "Расчёт растворимости CO\u2082 ещё не выполнен.\n\n"
                "Загрузите файл с данными — расчёт запустится автоматически."
            ),
            font=ctk.CTkFont(size=15),
            text_color=COLORS["text_secondary"],
            justify="center",
        )
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        # Subscribe to events
        self.event_bus.subscribe("solubility:ready", self._on_solubility_ready)
        self.event_bus.subscribe("solubility:switch", self._on_sol_plot_switch)
        self.event_bus.subscribe("file:clear", self._on_file_cleared)

        self.widget = self.root_frame
        return self.root_frame

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def display_figure(self, figure):
        """Embed a matplotlib figure, replacing the previous one."""
        if figure is None:
            return

        # Hide placeholder
        if self.placeholder:
            self.placeholder.place_forget()

        # Destroy previous canvas widgets
        if self.current_toolbar:
            self.current_toolbar.destroy()
            self.current_toolbar = None
        if self.toolbar_container:
            self.toolbar_container.destroy()
            self.toolbar_container = None
        for w in self.canvas_frame.winfo_children():
            if w is not self.placeholder:
                w.destroy()
        self.current_canvas = None

        # Embed new figure
        self.current_canvas = FigureCanvasTkAgg(figure, master=self.canvas_frame)
        self.current_canvas.draw()
        self.current_canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        # Toolbar strip
        self.toolbar_container = ctk.CTkFrame(
            self.canvas_frame,
            fg_color=COLORS["bg_secondary"],
            corner_radius=10,
            height=48,
        )
        self.toolbar_container.pack(fill="x", pady=(8, 6), padx=6)
        self.toolbar_container.pack_propagate(False)

        self.current_toolbar = NavigationToolbar2Tk(self.current_canvas, self.toolbar_container)
        self.current_toolbar.update()
        self.current_toolbar.pack(side="left", padx=8)

        # Zoom controls (identical to PlotArea)
        zoom_frame = ctk.CTkFrame(self.toolbar_container, fg_color="transparent")
        zoom_frame.pack(side="right", padx=12)

        hint = ctk.CTkLabel(
            zoom_frame,
            text="Колесо — зум  |  ПКМ — сдвиг",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        )
        hint.pack(side="left", padx=(0, 14))

        btn_in = ctk.CTkButton(
            zoom_frame,
            text="+",
            width=38,
            height=34,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            command=lambda: self._zoom(1.2),
        )
        btn_in.pack(side="left", padx=3)

        btn_out = ctk.CTkButton(
            zoom_frame,
            text="-",
            width=38,
            height=34,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            command=lambda: self._zoom(0.8),
        )
        btn_out.pack(side="left", padx=3)

        btn_reset = ctk.CTkButton(
            zoom_frame,
            text="Сброс",
            width=70,
            height=34,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color=COLORS["accent_warning"],
            hover_color=COLORS["accent_warning_hover"],
            text_color="#ffffff",
            corner_radius=8,
            command=self._reset_zoom,
        )
        btn_reset.pack(side="left", padx=3)

        self.zoom_controls = {
            "hint": hint,
            "btn_in": btn_in,
            "btn_out": btn_out,
            "btn_reset": btn_reset,
        }

        self._bind_mouse_events()

    def show_placeholder(self):
        """Restore the placeholder (called on file clear)."""
        if self.current_toolbar:
            self.current_toolbar.destroy()
            self.current_toolbar = None
        if self.toolbar_container:
            self.toolbar_container.destroy()
            self.toolbar_container = None
        for w in self.canvas_frame.winfo_children():
            if w is not self.placeholder:
                w.destroy()
        self.current_canvas = None
        self.zoom_controls = {}
        if self.placeholder and self.placeholder.winfo_exists():
            self.placeholder.place(relx=0.5, rely=0.5, anchor="center")
        # Reset tab button highlights
        self._update_tab_buttons("")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _switch_to(self, plot_id: str):
        """Switch display to the given solubility plot."""
        self.event_bus.publish("solubility:switch", plot_id)

    def _update_tab_buttons(self, active_id: str):
        for pid, btn in self.tab_buttons.items():
            if pid == active_id:
                btn.configure(
                    fg_color=COLORS["accent_primary"],
                    hover_color=COLORS["accent_secondary"],
                    text_color="#ffffff",
                    font=ctk.CTkFont(size=13, weight="bold"),
                )
            else:
                btn.configure(
                    fg_color=COLORS["bg_card"],
                    hover_color=COLORS["hover_light"],
                    text_color=COLORS["text_primary"],
                    font=ctk.CTkFont(size=13, weight="normal"),
                )

    # ------------------------------------------------------------------
    # Zoom / Pan (identical logic to PlotArea)
    # ------------------------------------------------------------------

    def _bind_mouse_events(self):
        if not self.current_canvas:
            return
        w = self.current_canvas.get_tk_widget()
        w.bind("<MouseWheel>", self._on_wheel)
        w.bind("<Button-4>", self._on_wheel)
        w.bind("<Button-5>", self._on_wheel)
        w.bind("<ButtonPress-2>", self._pan_start)
        w.bind("<B2-Motion>", self._pan_motion)
        w.bind("<ButtonRelease-2>", self._pan_end)
        w.bind("<ButtonPress-3>", self._pan_start)
        w.bind("<B3-Motion>", self._pan_motion)
        w.bind("<ButtonRelease-3>", self._pan_end)

    def _zoom(self, factor: float):
        if not self.current_canvas:
            return
        for ax in self.current_canvas.figure.get_axes():
            xl, yl = ax.get_xlim(), ax.get_ylim()
            xc = (xl[0] + xl[1]) / 2
            yc = (yl[0] + yl[1]) / 2
            new_left = xc - (xl[1] - xl[0]) / (2 * factor)
            new_right = xc + (xl[1] - xl[0]) / (2 * factor)
            new_bottom = yc - (yl[1] - yl[0]) / (2 * factor)
            new_top = yc + (yl[1] - yl[0]) / (2 * factor)
            ax.set_xlim(left=new_left, right=new_right)
            ax.set_ylim(bottom=new_bottom, top=new_top)
        self.current_canvas.draw_idle()
        self.current_canvas.flush_events()

    def _reset_zoom(self):
        if not self.current_canvas:
            return
        for ax in self.current_canvas.figure.get_axes():
            ax.autoscale()
        self.current_canvas.draw()

    def _on_wheel(self, event):
        if event.num == 5 or event.delta < 0:
            self._zoom(0.9)
        else:
            self._zoom(1.1)

    def _pan_start(self, event):
        self.pan_state.update(
            active=True,
            start_x=event.x,
            start_y=event.y,
            accumulated_dx=0,
            accumulated_dy=0,
        )

    def _pan_motion(self, event):
        if not self.current_canvas or not self.pan_state["active"]:
            return
        now = time.time() * 1000
        self.pan_state["accumulated_dx"] = event.x - self.pan_state["start_x"]
        self.pan_state["accumulated_dy"] = event.y - self.pan_state["start_y"]
        if now - self.pan_state.get("last_update", 0) < 16:
            if not self.pan_state.get("pending_update"):
                self.pan_state["pending_update"] = self.parent.after(16, self._do_pan)
            return
        self._do_pan()

    def _do_pan(self):
        if not self.current_canvas or not self.pan_state["active"]:
            self.pan_state["pending_update"] = None
            return
        dx = self.pan_state["accumulated_dx"]
        dy = self.pan_state["accumulated_dy"]
        if dx == 0 and dy == 0:
            self.pan_state["pending_update"] = None
            return
        w = self.current_canvas.get_tk_widget()
        cw, ch = w.winfo_width(), w.winfo_height()
        for ax in self.current_canvas.figure.get_axes():
            xl, yl = ax.get_xlim(), ax.get_ylim()
            if cw > 0 and ch > 0:
                new_left = xl[0] - dx / cw * (xl[1] - xl[0])
                new_right = xl[1] - dx / cw * (xl[1] - xl[0])
                new_bottom = yl[0] + dy / ch * (yl[1] - yl[0])
                new_top = yl[1] + dy / ch * (yl[1] - yl[0])
                ax.set_xlim(left=new_left, right=new_right)
                ax.set_ylim(bottom=new_bottom, top=new_top)
        self.pan_state["start_x"] += dx
        self.pan_state["start_y"] += dy
        self.pan_state["accumulated_dx"] = 0
        self.pan_state["accumulated_dy"] = 0
        self.pan_state["last_update"] = time.time() * 1000
        self.pan_state["pending_update"] = None
        self.current_canvas.draw_idle()
        self.current_canvas.flush_events()

    def _pan_end(self, event):
        if self.pan_state.get("pending_update"):
            self.parent.after_cancel(self.pan_state["pending_update"])
        if self.pan_state["active"]:
            self._do_pan()
        self.pan_state["active"] = False
        self.pan_state["pending_update"] = None
        if self.current_canvas:
            self.current_canvas.draw()

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_solubility_ready(self, _data=None):
        """Show first plot when calculation finishes."""
        order = self.app_state.sol_plot_order
        if order:
            first = self.app_state.current_sol_plot or order[0]
            if first not in self.app_state.solubility_figures:
                first = order[0]
            self._update_tab_buttons(first)
            fig = self.app_state.solubility_figures.get(first)
            if fig:
                self.display_figure(fig)

    def _on_sol_plot_switch(self, plot_id: str):
        """Handle tab switch event."""
        self.app_state.current_sol_plot = plot_id
        self._update_tab_buttons(plot_id)
        fig = self.app_state.solubility_figures.get(plot_id)
        if fig:
            self.display_figure(fig)

    def _on_file_cleared(self, _data=None):
        self.show_placeholder()

    # ------------------------------------------------------------------
    # Theme
    # ------------------------------------------------------------------

    def update_theme(self):
        if self.root_frame:
            self.root_frame.configure(
                fg_color=COLORS["bg_secondary"],
                border_color=COLORS["border"],
            )
        if self.canvas_frame:
            self.canvas_frame.configure(fg_color=COLORS["bg_card"])
        if self.placeholder:
            try:
                self.placeholder.configure(text_color=COLORS["text_secondary"])
            except Exception:
                pass
        if self.toolbar_container:
            try:
                self.toolbar_container.configure(fg_color=COLORS["bg_secondary"])
            except Exception:
                pass
        if self.zoom_controls:
            if "hint" in self.zoom_controls:
                self.zoom_controls["hint"].configure(text_color=COLORS["text_secondary"])
            for k in ("btn_in", "btn_out"):
                if k in self.zoom_controls:
                    self.zoom_controls[k].configure(
                        fg_color=COLORS["bg_card"],
                        hover_color=COLORS["hover_light"],
                        text_color=COLORS["text_primary"],
                    )
            if "btn_reset" in self.zoom_controls:
                self.zoom_controls["btn_reset"].configure(
                    fg_color=COLORS["accent_warning"],
                    hover_color=COLORS["accent_warning_hover"],
                )
        # Re-apply tab button styles
        self._update_tab_buttons(self.app_state.current_sol_plot)

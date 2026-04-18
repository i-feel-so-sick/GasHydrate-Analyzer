"""
Plot area component with canvas and zoom/pan controls.
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


class PlotArea(BaseComponent):
    """
    Plot display area with matplotlib canvas, toolbar, and zoom/pan controls.
    """

    def __init__(self, parent: ctk.CTk, app_state: AppState, event_bus: EventBus):
        super().__init__(parent, app_state, event_bus)

        # UI elements
        self.plot_frame = None
        self.canvas_frame = None
        self.placeholder = None
        self.placeholder_text = None
        self.placeholder_hint = None

        # Current canvas and toolbar
        self.current_canvas = None
        self.current_toolbar = None
        self.toolbar_container = None
        self.zoom_controls = {}  # Store references for theme update

        # Pan state with throttling
        self.pan_state = {
            "active": False,
            "start_x": 0,
            "start_y": 0,
            "last_update": 0,
            "pending_update": None,
            "accumulated_dx": 0,
            "accumulated_dy": 0,
        }

    def build(self) -> ctk.CTkFrame:
        """Build plot area."""
        self.plot_frame = ctk.CTkFrame(
            self.parent,
            corner_radius=12,
            fg_color=COLORS["bg_secondary"],
            border_width=1,
            border_color=COLORS["border"],
        )

        # Canvas frame
        self.canvas_frame = ctk.CTkFrame(
            self.plot_frame, fg_color=COLORS["bg_card"], corner_radius=12
        )
        self.canvas_frame.pack(fill="both", expand=True, padx=12, pady=12)

        # Placeholder for initial state
        self.placeholder = ctk.CTkFrame(self.canvas_frame, fg_color="transparent")
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

        self.placeholder_text = ctk.CTkLabel(
            self.placeholder,
            text="Загрузите файл для визуализации",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["text_secondary"],
        )
        self.placeholder_text.pack()

        self.placeholder_hint = ctk.CTkLabel(
            self.placeholder,
            text="Перетащите файл сюда или нажмите 'Открыть'",
            font=ctk.CTkFont(size=14),
            text_color=COLORS["text_secondary"],
        )
        self.placeholder_hint.pack(pady=(8, 0))

        # Subscribe to events
        self.event_bus.subscribe("plot:switch", self._on_plot_switch)
        self.event_bus.subscribe("plot:generated", self._on_plots_generated)
        self.event_bus.subscribe("file:clear", self._on_file_cleared)

        self.widget = self.plot_frame
        return self.plot_frame

    def display_plot(self, figure):
        """Display a matplotlib figure."""
        if not figure:
            return

        # Hide placeholder
        if self.placeholder:
            self.placeholder.place_forget()

        # Clean up previous toolbar and canvas to avoid memory leaks
        if self.current_toolbar:
            self.current_toolbar.destroy()
            self.current_toolbar = None
        if self.current_canvas:
            self.current_canvas = None

        # Clear previous canvas widgets
        for widget in self.canvas_frame.winfo_children() if self.canvas_frame else []:
            if widget != self.placeholder:
                widget.destroy()

        # Create canvas
        self.current_canvas = FigureCanvasTkAgg(figure, master=self.canvas_frame)
        self.current_canvas.draw()
        self.current_canvas.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=6)

        # Add compact toolbar
        self.toolbar_container = ctk.CTkFrame(
            self.canvas_frame, fg_color=COLORS["bg_secondary"], corner_radius=10, height=48
        )
        self.toolbar_container.pack(fill="x", pady=(8, 6), padx=6)
        self.toolbar_container.pack_propagate(False)

        # Matplotlib toolbar
        self.current_toolbar = NavigationToolbar2Tk(self.current_canvas, self.toolbar_container)
        self.current_toolbar.update()
        self.current_toolbar.pack(side="left", padx=8)

        # Zoom controls
        zoom_frame = ctk.CTkFrame(self.toolbar_container, fg_color="transparent")
        zoom_frame.pack(side="right", padx=12)

        hint_label = ctk.CTkLabel(
            zoom_frame,
            text="Колесо — зум  |  ПКМ — сдвиг",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
        )
        hint_label.pack(side="left", padx=(0, 14))

        btn_zoom_in = ctk.CTkButton(
            zoom_frame,
            text="+",
            width=38,
            height=34,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            command=lambda: self._zoom_current(1.2),
        )
        btn_zoom_in.pack(side="left", padx=3)

        btn_zoom_out = ctk.CTkButton(
            zoom_frame,
            text="-",
            width=38,
            height=34,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color=COLORS["bg_card"],
            hover_color=COLORS["hover_light"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            command=lambda: self._zoom_current(0.8),
        )
        btn_zoom_out.pack(side="left", padx=3)

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
            command=self._reset_current_zoom,
        )
        btn_reset.pack(side="left", padx=3)

        # Store references for theme update
        self.zoom_controls = {
            "hint_label": hint_label,
            "btn_zoom_in": btn_zoom_in,
            "btn_zoom_out": btn_zoom_out,
            "btn_reset": btn_reset,
        }

        # Bind mouse events for zoom/pan
        self._bind_mouse_events()

    def _bind_mouse_events(self):
        """Bind mouse events for zoom and pan."""
        if not self.current_canvas:
            return

        canvas_widget = self.current_canvas.get_tk_widget()

        # Mouse wheel zoom
        canvas_widget.bind("<MouseWheel>", self._on_mouse_wheel_current)
        canvas_widget.bind("<Button-4>", self._on_mouse_wheel_current)
        canvas_widget.bind("<Button-5>", self._on_mouse_wheel_current)

        # Pan with middle/right mouse button
        canvas_widget.bind("<ButtonPress-2>", self._on_pan_start_current)
        canvas_widget.bind("<B2-Motion>", self._on_pan_motion_current)
        canvas_widget.bind("<ButtonRelease-2>", self._on_pan_end_current)
        canvas_widget.bind("<ButtonPress-3>", self._on_pan_start_current)
        canvas_widget.bind("<B3-Motion>", self._on_pan_motion_current)
        canvas_widget.bind("<ButtonRelease-3>", self._on_pan_end_current)

    def _zoom_current(self, scale_factor: float):
        """Zoom current plot."""
        if not self.current_canvas:
            return
        fig = self.current_canvas.figure
        for ax in fig.get_axes():
            xlim, ylim = ax.get_xlim(), ax.get_ylim()
            x_center, y_center = (xlim[0] + xlim[1]) / 2, (ylim[0] + ylim[1]) / 2
            x_range = (xlim[1] - xlim[0]) / scale_factor
            y_range = (ylim[1] - ylim[0]) / scale_factor
            ax.set_xlim(x_center - x_range / 2, x_center + x_range / 2)
            ax.set_ylim(y_center - y_range / 2, y_center + y_range / 2)
        self.current_canvas.draw_idle()
        self.current_canvas.flush_events()

    def _reset_current_zoom(self):
        """Reset zoom on current plot."""
        if not self.current_canvas:
            return
        for ax in self.current_canvas.figure.get_axes():
            ax.autoscale()
        self.current_canvas.draw()

    def _on_mouse_wheel_current(self, event):
        """Handle mouse wheel zoom."""
        if not self.current_canvas:
            return
        if event.num == 5 or event.delta < 0:
            self._zoom_current(0.9)
        elif event.num == 4 or event.delta > 0:
            self._zoom_current(1.1)

    def _on_pan_start_current(self, event):
        """Start panning."""
        if not self.current_canvas:
            return
        self.pan_state["active"] = True
        self.pan_state["start_x"] = event.x
        self.pan_state["start_y"] = event.y
        self.pan_state["accumulated_dx"] = 0
        self.pan_state["accumulated_dy"] = 0

    def _on_pan_motion_current(self, event):
        """Pan with throttling for smoothness."""
        if not self.current_canvas or not self.pan_state.get("active"):
            return

        current_time = time.time() * 1000  # ms

        dx = event.x - self.pan_state["start_x"]
        dy = event.y - self.pan_state["start_y"]

        if dx == 0 and dy == 0:
            return

        # Accumulate movement
        self.pan_state["accumulated_dx"] = dx
        self.pan_state["accumulated_dy"] = dy

        # Throttle: update at most every 16ms (~60fps)
        time_since_last = current_time - self.pan_state.get("last_update", 0)
        if time_since_last < 16:
            # Schedule update if not already scheduled
            if not self.pan_state.get("pending_update"):
                self.pan_state["pending_update"] = self.parent.after(
                    int(16 - time_since_last), self._do_pan_update
                )
            return

        self._do_pan_update()

    def _do_pan_update(self):
        """Perform the actual pan update."""
        if not self.current_canvas or not self.pan_state.get("active"):
            self.pan_state["pending_update"] = None
            return

        dx = self.pan_state.get("accumulated_dx", 0)
        dy = self.pan_state.get("accumulated_dy", 0)

        if dx == 0 and dy == 0:
            self.pan_state["pending_update"] = None
            return

        for ax in self.current_canvas.figure.get_axes():
            xlim = ax.get_xlim()
            ylim = ax.get_ylim()
            x_range = xlim[1] - xlim[0]
            y_range = ylim[1] - ylim[0]

            # Get canvas size for scaling
            canvas_widget = self.current_canvas.get_tk_widget()
            canvas_width = canvas_widget.winfo_width()
            canvas_height = canvas_widget.winfo_height()

            if canvas_width > 0 and canvas_height > 0:
                x_shift = -(dx / canvas_width) * x_range
                y_shift = (dy / canvas_height) * y_range
                ax.set_xlim(xlim[0] + x_shift, xlim[1] + x_shift)
                ax.set_ylim(ylim[0] + y_shift, ylim[1] + y_shift)

        # Update start position for incremental panning
        self.pan_state["start_x"] += dx
        self.pan_state["start_y"] += dy
        self.pan_state["accumulated_dx"] = 0
        self.pan_state["accumulated_dy"] = 0
        self.pan_state["last_update"] = time.time() * 1000
        self.pan_state["pending_update"] = None

        # Use blit for faster rendering
        self.current_canvas.draw_idle()
        self.current_canvas.flush_events()

    def _on_pan_end_current(self, event):
        """End panning."""
        # Cancel any pending update
        if self.pan_state.get("pending_update"):
            self.parent.after_cancel(self.pan_state["pending_update"])

        # Do final update with accumulated movement
        if self.pan_state.get("active"):
            self._do_pan_update()

        self.pan_state["active"] = False
        self.pan_state["pending_update"] = None

        # Final redraw
        if self.current_canvas:
            self.current_canvas.draw()

    def show_placeholder(self):
        """Show placeholder text."""
        self.current_canvas = None
        self.current_toolbar = None
        self.toolbar_container = None
        self.zoom_controls = {}

        # Clear canvas
        for widget in self.canvas_frame.winfo_children():
            if widget != self.placeholder:
                widget.destroy()
        self.placeholder.place(relx=0.5, rely=0.5, anchor="center")

    # Public methods for MainWindow
    def reset_zoom(self):
        """Reset zoom (public interface)."""
        self._reset_current_zoom()

    def zoom_in(self):
        """Zoom in (public interface)."""
        self._zoom_current(1.2)

    def zoom_out(self):
        """Zoom out (public interface)."""
        self._zoom_current(0.8)

    def _on_plot_switch(self, plot_id):
        """Handle plot switch event."""
        if plot_id in self.app_state.figures:
            self.display_plot(self.app_state.figures[plot_id])

    def _on_plots_generated(self, data):
        """Handle plots generated event."""
        # Display current plot
        current_id = self.app_state.current_plot_id
        if current_id in self.app_state.figures:
            self.display_plot(self.app_state.figures[current_id])

    def _on_file_cleared(self, data):
        """Handle file cleared event."""
        self.show_placeholder()

    def update_theme(self):
        """Update theme colors."""
        self.plot_frame.configure(fg_color=COLORS["bg_secondary"], border_color=COLORS["border"])
        self.canvas_frame.configure(fg_color=COLORS["bg_card"])

        if self.placeholder_text:
            self.placeholder_text.configure(text_color=COLORS["text_secondary"])
        if self.placeholder_hint:
            self.placeholder_hint.configure(text_color=COLORS["text_secondary"])

        # Update toolbar container and controls
        if self.toolbar_container:
            self.toolbar_container.configure(fg_color=COLORS["bg_secondary"])

        if self.zoom_controls:
            if "hint_label" in self.zoom_controls:
                self.zoom_controls["hint_label"].configure(text_color=COLORS["text_secondary"])
            if "btn_zoom_in" in self.zoom_controls:
                self.zoom_controls["btn_zoom_in"].configure(
                    fg_color=COLORS["bg_card"],
                    hover_color=COLORS["hover_light"],
                    text_color=COLORS["text_primary"],
                )
            if "btn_zoom_out" in self.zoom_controls:
                self.zoom_controls["btn_zoom_out"].configure(
                    fg_color=COLORS["bg_card"],
                    hover_color=COLORS["hover_light"],
                    text_color=COLORS["text_primary"],
                )
            if "btn_reset" in self.zoom_controls:
                self.zoom_controls["btn_reset"].configure(
                    fg_color=COLORS["accent_warning"], hover_color=COLORS["accent_warning_hover"]
                )

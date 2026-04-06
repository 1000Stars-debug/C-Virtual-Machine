#!/usr/bin/python3
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import json
import os
import copy

class DraggableCommentBox:
	def __init__(self, editor, x, y, text="", is_expanded=True):
		self.editor = editor
		self.canvas = editor.canvas
		self.is_expanded = is_expanded
		self.text_content = text
		self.is_dragging = False 
		self.uid = f"comment_{id(self)}"
		tag_c = ("comment", self.uid)
		self.width = 160
		self.header_height = 25
		self.bg_color = "#FFF59D" 
		self.rect_id = self.canvas.create_rectangle(x, y, x + self.width, y + self.header_height, fill=self.bg_color, outline="#D4E157", width=2, tags=tag_c)
		self.title_id = self.canvas.create_text(x + 5, y + 12, text="📝 Note", anchor="w", font=("Consolas", 10, "bold"), fill="#333", tags=tag_c)
		self.toggle_id = self.canvas.create_text(x + self.width - 15, y + 12, text="[-]" if is_expanded else "[+]", font=("Consolas", 10, "bold"), fill="#333", tags=tag_c)
		self.text_widget = None
		self.text_window_id = None
		if self.editor.zoom_level != 1.0:
			self.canvas.scale(self.uid, x, y, self.editor.zoom_level, self.editor.zoom_level)
		if self.is_expanded:
			self.show_text()
		self.canvas.tag_bind(self.rect_id, "<ButtonPress-1>", self.on_press)
		self.canvas.tag_bind(self.title_id, "<ButtonPress-1>", self.on_press)
		self.canvas.tag_bind(self.toggle_id, "<ButtonPress-1>", self.toggle)
		self.canvas.tag_bind(self.rect_id, "<B1-Motion>", self.on_drag)
		self.canvas.tag_bind(self.title_id, "<B1-Motion>", self.on_drag)
		for t in (self.rect_id, self.title_id, self.toggle_id):
			self.canvas.tag_bind(t, "<Button-3>", self.delete_self)
			self.canvas.tag_bind(t, "<Button-2>", self.delete_self)
		self.raw_start_cx = 0
		self.raw_start_cy = 0
		self.drag_start_x = 0
		self.drag_start_y = 0

	def toggle(self, event=None):
		self.is_expanded = not self.is_expanded
		self.canvas.itemconfig(self.toggle_id, text="[-]" if self.is_expanded else "[+]")
		if self.is_expanded:
			self.show_text()
		else:
			self.hide_text()
		self.editor.save_history_state()

	def show_text(self):
		coords = self.canvas.coords(self.rect_id)
		x, y = coords[0], coords[1]
		z = self.editor.zoom_level
		self.text_widget = tk.Text(self.canvas, width=18, height=6, font=("Consolas", 10), bg=self.bg_color, fg="#333", wrap="word", relief="flat")
		self.text_widget.insert("1.0", self.text_content)
		self.text_widget.bind("<KeyRelease>", self.update_text)
		self.text_widget.bind("<FocusOut>", lambda e: self.editor.save_history_state())
		self.canvas.coords(self.rect_id, x, y, x + self.width * z, y + (self.header_height + 105) * z)
		self.text_window_id = self.canvas.create_window(x + (self.width/2) * z, y + (self.header_height + 50) * z, window=self.text_widget, tags=("comment", self.uid))

	def hide_text(self):
		if self.text_window_id:
			self.canvas.delete(self.text_window_id)
			self.text_window_id = None
			self.text_widget = None
		coords = self.canvas.coords(self.rect_id)
		x, y = coords[0], coords[1]
		z = self.editor.zoom_level
		self.canvas.coords(self.rect_id, x, y, x + self.width * z, y + self.header_height * z)

	def update_text(self, event):
		self.text_content = self.text_widget.get("1.0", "end-1c")

	def on_press(self, event):
		self.canvas.focus_set()
		if event:
			self.raw_start_cx = self.canvas.canvasx(event.x)
			self.raw_start_cy = self.canvas.canvasy(event.y)
		coords = self.canvas.coords(self.rect_id)
		if coords:
			self.drag_start_x = coords[0]
			self.drag_start_y = coords[1]
		self.canvas.tag_raise(self.rect_id)
		self.canvas.tag_raise(self.title_id)
		self.canvas.tag_raise(self.toggle_id)
		if self.text_window_id:
			self.canvas.tag_raise(self.text_window_id)

	def on_drag(self, event):
		self.is_dragging = True
		self.editor.drag_occurred = True
		cx = self.canvas.canvasx(event.x)
		cy = self.canvas.canvasy(event.y)
		total_dx = cx - self.raw_start_cx
		total_dy = cy - self.raw_start_cy
		target_x = self.drag_start_x + total_dx
		target_y = self.drag_start_y + total_dy
		if self.editor.snap_enabled:
			step = 20 * self.editor.zoom_level
			target_x = round(target_x / step) * step
			target_y = round(target_y / step) * step
		curr_coords = self.canvas.coords(self.rect_id)
		if not curr_coords: return
		move_dx = target_x - curr_coords[0]
		move_dy = target_y - curr_coords[1]
		if move_dx != 0 or move_dy != 0:
			self.canvas.move(self.rect_id, move_dx, move_dy)
			self.canvas.move(self.title_id, move_dx, move_dy)
			self.canvas.move(self.toggle_id, move_dx, move_dy)
			if self.text_window_id:
				self.canvas.move(self.text_window_id, move_dx, move_dy)

	def snap_to_grid(self):
		coords = self.canvas.coords(self.rect_id)
		if not coords: return
		x, y = coords[0], coords[1]
		step = 20 * self.editor.zoom_level
		target_x = round(x / step) * step
		target_y = round(y / step) * step
		dx = target_x - x
		dy = target_y - y
		if dx == 0 and dy == 0: return
		self.canvas.move(self.rect_id, dx, dy)
		self.canvas.move(self.title_id, dx, dy)
		self.canvas.move(self.toggle_id, dx, dy)
		if self.text_window_id:
			self.canvas.move(self.text_window_id, dx, dy)

	def delete_self(self, event=None):
		self.canvas.delete(self.rect_id)
		self.canvas.delete(self.title_id)
		self.canvas.delete(self.toggle_id)
		if self.text_window_id:
			self.canvas.delete(self.text_window_id)
		if self in self.editor.comments:
			self.editor.comments.remove(self)

	def get_state(self):
		coords = self.canvas.coords(self.rect_id)
		return {
			"x": coords[0],
			"y": coords[1],
			"text": self.text_content,
			"is_expanded": self.is_expanded
		}

class DraggableBlock:
	def __init__(self, editor, x, y, opcode, category, has_input=False):
		self.editor = editor
		self.canvas = editor.canvas
		self.opcode = opcode
		self.has_input = has_input
		self.category = category
		self.is_dragging = False 
		self.uid = f"block_{id(self)}"
		tag_b = ("block", self.uid)
		colors = {
			"Core": "#A2D149",
			"Math": "#4DB6AC",
			"Control": "#FFB74D",
			"Hardware": "#BA68C8",
			"UI": "#4FC3F7",
			"System": "#E57373"
		}
		color = colors.get(category, "white")
		self.width = 130
		self.height = 40
		self.rect_id = self.canvas.create_rectangle(x, y, x + self.width, y + self.height, fill=color, outline="#222", width=2, tags=tag_b)
		self.text_id = self.canvas.create_text(x + 10, y + 20, text=opcode, anchor="w", font=("Consolas", 10, "bold"), tags=tag_b)
		self.entry_window = None
		self.entry = None
		if has_input:
			self.entry = tk.Entry(self.canvas, width=6, justify="center", font=("Consolas", 10))
			if opcode == "PUSH":
				default_text = "0"
			elif opcode == "LABEL":
				default_text = "loop"
			else:
				default_text = "0"
			self.entry.insert(0, default_text)
			self.entry_window = self.canvas.create_window(x + 100, y + 20, window=self.entry, tags=tag_b)
			self.entry.bind("<KeyRelease>", lambda e: self.editor.update_connections())
			self.entry.bind("<FocusOut>", lambda e: self.editor.save_history_state())
		if self.editor.zoom_level != 1.0:
			self.canvas.scale(self.uid, x, y, self.editor.zoom_level, self.editor.zoom_level)
		self.canvas.tag_bind(self.rect_id, "<ButtonPress-1>", self.on_press)
		self.canvas.tag_bind(self.text_id, "<ButtonPress-1>", self.on_press)
		self.canvas.tag_bind(self.rect_id, "<B1-Motion>", self.on_drag)
		self.canvas.tag_bind(self.text_id, "<B1-Motion>", self.on_drag)
		self.canvas.tag_bind(self.rect_id, "<Button-3>", self.delete_self)
		self.canvas.tag_bind(self.text_id, "<Button-3>", self.delete_self)
		self.canvas.tag_bind(self.rect_id, "<Button-2>", self.delete_self)
		self.canvas.tag_bind(self.text_id, "<Button-2>", self.delete_self)
		self.raw_start_cx = 0
		self.raw_start_cy = 0
		self.drag_start_x = 0
		self.drag_start_y = 0

	def on_press(self, event):
		self.canvas.focus_set() 
		if event:
			self.raw_start_cx = self.canvas.canvasx(event.x)
			self.raw_start_cy = self.canvas.canvasy(event.y)
			if self not in self.editor.selected_blocks:
				if not (event.state & 0x0001): 
					self.editor.clear_selection()
				self.editor.select_block(self)
		for b in self.editor.selected_blocks:
			coords = self.canvas.coords(b.rect_id)
			if coords:
				b.drag_start_x = coords[0]
				b.drag_start_y = coords[1]
			self.canvas.tag_raise(b.rect_id)
			self.canvas.tag_raise(b.text_id)
			if b.entry_window:
				self.canvas.tag_raise(b.entry_window)

	def on_drag(self, event):
		self.editor.drag_occurred = True
		cx = self.canvas.canvasx(event.x)
		cy = self.canvas.canvasy(event.y)
		total_dx = cx - self.raw_start_cx
		total_dy = cy - self.raw_start_cy
		moved_any = False
		for b in self.editor.selected_blocks:
			b.is_dragging = True 
			target_x = b.drag_start_x + total_dx
			target_y = b.drag_start_y + total_dy
			if self.editor.snap_enabled:
				step = 20 * self.editor.zoom_level
				target_x = round(target_x / step) * step
				target_y = round(target_y / step) * step
			curr_coords = self.canvas.coords(b.rect_id)
			if not curr_coords: continue
			move_dx = target_x - curr_coords[0]
			move_dy = target_y - curr_coords[1]
			if move_dx != 0 or move_dy != 0:
				moved_any = True
				self.canvas.move(b.rect_id, move_dx, move_dy)
				self.canvas.move(b.text_id, move_dx, move_dy)
				if b.entry_window:
					self.canvas.move(b.entry_window, move_dx, move_dy)
		if moved_any:
			self.editor.update_connections()

	def snap_to_grid(self):
		coords = self.canvas.coords(self.rect_id)
		if not coords: return
		x, y = coords[0], coords[1]
		step = 20 * self.editor.zoom_level
		target_x = round(x / step) * step
		target_y = round(y / step) * step
		dx = target_x - x
		dy = target_y - y
		if dx == 0 and dy == 0: return
		self.canvas.move(self.rect_id, dx, dy)
		self.canvas.move(self.text_id, dx, dy)
		if self.entry_window:
			self.canvas.move(self.entry_window, dx, dy)

	def delete_self(self, event=None):
		if self in self.editor.selected_blocks:
			self.editor.deselect_block(self)
		self.canvas.delete(self.rect_id)
		self.canvas.delete(self.text_id)
		if self.entry_window:
			self.canvas.delete(self.entry_window)
		if self in self.editor.blocks:
			self.editor.blocks.remove(self)
		self.editor.update_connections()

	def get_y_position(self):
		return self.canvas.coords(self.rect_id)[1]

	def get_code(self):
		if self.opcode == "LABEL":
			return f"\n{self.entry.get()}:"
		if self.has_input:
			return f"\t{self.opcode} {self.entry.get()}"
		return f"\t{self.opcode}"

	def get_state(self):
		coords = self.canvas.coords(self.rect_id)
		return {
			"x": coords[0],
			"y": coords[1],
			"opcode": self.opcode,
			"category": self.category,
			"has_input": self.has_input,
			"value": self.entry.get() if self.has_input else ""
		}

class VisualAssemblyEditor:
	def __init__(self, root):
		self.root = root
		self.root.title("CVM Engine - Visual Editor")
		self.root.geometry("1100x800")
		self.blocks = []
		self.comments = []
		self.data_entries = {} 
		self.selected_blocks = set()
		self.current_filepath = None 
		self.compile_filepath = None
		self.zoom_level = 1.0
		self.snap_enabled = True
		self.drag_occurred = False
		self.history = []
		self.history_index = -1
		self._is_restoring = False
		self.build_topbar()
		self.sidebar_frame = tk.Frame(self.root, width=280, bg="#333")
		self.sidebar_frame.pack(side="left", fill="y")
		self.sidebar_frame.pack_propagate(False)
		self.canvas = tk.Canvas(self.root, bg="#282C34", scrollregion=(-50000, -50000, 50000, 50000))
		self.canvas.pack(side="right", fill="both", expand=True)
		self.root.update_idletasks()
		self.canvas.xview_moveto(0.5)
		self.canvas.yview_moveto(0.5)
		self.bind_workspace_controls()
		self.notebook = ttk.Notebook(self.sidebar_frame)
		self.notebook.pack(fill="both", expand=True)
		self.toolbox_tab = tk.Frame(self.notebook, bg="#333")
		self.data_tab = tk.Frame(self.notebook, bg="#333")
		self.notebook.add(self.toolbox_tab, text="Toolbox")
		self.notebook.add(self.data_tab, text="Data Assets")
		self.build_toolbox()
		self.build_data_manager()
		self.save_history_state()

	def get_workspace_state(self):
		return {
			"data_entries": copy.deepcopy(self.data_entries),
			"blocks": [b.get_state() for b in self.blocks],
			"comments": [c.get_state() for c in self.comments]
		}

	def save_history_state(self):
		if self._is_restoring: return
		current_state = self.get_workspace_state()
		if self.history and self.history_index >= 0:
			if current_state == self.history[self.history_index]:
				return
		if self.history_index < len(self.history) - 1:
			self.history = self.history[:self.history_index + 1]
		self.history.append(current_state)
		if len(self.history) > 50:
			self.history.pop(0)
		else:
			self.history_index += 1

	def apply_workspace_state(self, state):
		self._is_restoring = True
		for b in list(self.blocks): b.delete_self(None)
		for c in list(self.comments): c.delete_self(None)
		self.blocks.clear()
		self.comments.clear()
		self.selected_blocks.clear()
		self.data_entries.clear()
		self.canvas.delete("connection")
		self.canvas.delete("sel_rect")
		self.data_entries = copy.deepcopy(state.get("data_entries", {}))
		self.refresh_data_list()
		target_zoom = self.zoom_level
		self.zoom_level = 1.0
		for b in state.get("blocks", []):
			x, y = b["x"] / target_zoom, b["y"] / target_zoom
			new_block = DraggableBlock(self, x, y, b["opcode"], b["category"], b["has_input"])
			if b["has_input"]:
				new_block.entry.delete(0, tk.END)
				new_block.entry.insert(0, b.get("value", ""))
			self.blocks.append(new_block)
		for c in state.get("comments", []):
			x, y = c["x"] / target_zoom, c["y"] / target_zoom
			new_comment = DraggableCommentBox(self, x, y, c.get("text", ""), c.get("is_expanded", True))
			self.comments.append(new_comment)
		if target_zoom != 1.0:
			self.canvas.scale("all", 0, 0, target_zoom, target_zoom)
		self.zoom_level = target_zoom
		self.update_connections()
		self.redraw_grid()
		self._is_restoring = False

	def undo(self, event=None):
		if self.history_index > 0:
			self.history_index -= 1
			self.apply_workspace_state(self.history[self.history_index])

	def redo(self, event=None):
		if self.history_index < len(self.history) - 1:
			self.history_index += 1
			self.apply_workspace_state(self.history[self.history_index])

	def bind_workspace_controls(self):
		self.canvas.bind("<Configure>", lambda e: self.redraw_grid())
		self.canvas.bind("<ButtonPress-2>", self.pan_start)
		self.canvas.bind("<B2-Motion>", self.pan_move)
		self.canvas.bind("<Control-MouseWheel>", self.zoom)
		self.canvas.bind("<Control-Button-4>", self.zoom) 
		self.canvas.bind("<Control-Button-5>", self.zoom) 
		self.canvas.bind("<ButtonPress-1>", self.box_select_start)
		self.canvas.bind("<B1-Motion>", self.box_select_move)
		self.canvas.bind("<ButtonRelease-1>", self.on_global_release)
		self.root.bind("<Delete>", self.delete_selected_blocks)
		self.root.bind("<BackSpace>", self.delete_selected_blocks)
		self.root.bind("<Control-d>", self.duplicate_selected_blocks)
		self.root.bind("<Control-D>", self.duplicate_selected_blocks)
		self.root.bind("<Control-z>", self.undo)
		self.root.bind("<Control-Z>", self.undo)
		self.root.bind("<Control-y>", self.redo)
		self.root.bind("<Control-Y>", self.redo)
		self.root.bind("<Control-s>", lambda e: self.save_project())
		self.root.bind("<Control-S>", lambda e: self.save_project())

	def on_global_release(self, event):
		self.box_select_end(event)
		if self.snap_enabled:
			for b in self.blocks:
				if getattr(b, 'is_dragging', False):
					b.snap_to_grid()
					b.is_dragging = False
			for c in self.comments:
				if getattr(c, 'is_dragging', False):
					c.snap_to_grid()
					c.is_dragging = False
			self.update_connections()
		if self.drag_occurred:
			self.save_history_state()
			self.drag_occurred = False

	def delete_selected_blocks(self, event=None):
		if isinstance(self.root.focus_get(), tk.Entry) or isinstance(self.root.focus_get(), tk.Text):
			return
		if not self.selected_blocks:
			return
		for block in list(self.selected_blocks):
			block.delete_self(None)
		self.selected_blocks.clear()
		self.save_history_state()

	def duplicate_selected_blocks(self, event=None):
		if isinstance(self.root.focus_get(), tk.Entry) or isinstance(self.root.focus_get(), tk.Text):
			return
		if not self.selected_blocks:
			return
		blocks_to_copy = list(self.selected_blocks)
		self.clear_selection()
		offset_px = 30 
		for b in blocks_to_copy:
			state = b.get_state()
			new_block = DraggableBlock(self, state["x"] + offset_px, state["y"] + offset_px, state["opcode"], state["category"], state["has_input"])
			if state["has_input"]:
				new_block.entry.delete(0, tk.END)
				new_block.entry.insert(0, state["value"])
			self.blocks.append(new_block)
			self.select_block(new_block) 
		self.update_connections()
		self.save_history_state()

	def pan_start(self, event):
		self.canvas.scan_mark(event.x, event.y)

	def pan_move(self, event):
		self.canvas.scan_dragto(event.x, event.y, gain=1)
		self.update_connections()
		self.redraw_grid()

	def zoom(self, event):
		scale = 1.1 if (getattr(event, 'delta', 0) > 0 or event.num == 4) else 0.9
		self.zoom_level *= scale
		cx = self.canvas.canvasx(event.x)
		cy = self.canvas.canvasy(event.y)
		self.canvas.scale("all", cx, cy, scale, scale)
		self.update_connections()
		self.redraw_grid()

	def box_select_start(self, event):
		self.canvas.focus_set()
		item = self.canvas.find_withtag("current")
		if item and ("block" in self.canvas.gettags(item[0]) or "comment" in self.canvas.gettags(item[0])):
			return 
		if not (event.state & 0x0001): 
			self.clear_selection()
		self.sel_start_x = self.canvas.canvasx(event.x)
		self.sel_start_y = self.canvas.canvasy(event.y)
		self.sel_rect = self.canvas.create_rectangle(self.sel_start_x, self.sel_start_y, self.sel_start_x, self.sel_start_y, outline="#4FC3F7", dash=(4, 4), tags="sel_rect")

	def box_select_move(self, event):
		if hasattr(self, 'sel_rect') and self.sel_rect:
			cur_x = self.canvas.canvasx(event.x)
			cur_y = self.canvas.canvasy(event.y)
			self.canvas.coords(self.sel_rect, self.sel_start_x, self.sel_start_y, cur_x, cur_y)

	def box_select_end(self, event):
		if hasattr(self, 'sel_rect') and self.sel_rect:
			coords = self.canvas.coords(self.sel_rect)
			self.canvas.delete(self.sel_rect)
			self.sel_rect = None
			if len(coords) == 4:
				x1, y1, x2, y2 = coords
				x1, x2 = min(x1, x2), max(x1, x2)
				y1, y2 = min(y1, y2), max(y1, y2)
				enclosed_items = self.canvas.find_enclosed(x1, y1, x2, y2)
				for block in self.blocks:
					if block.rect_id in enclosed_items:
						self.select_block(block)

	def select_block(self, block):
		self.selected_blocks.add(block)
		self.canvas.itemconfig(block.rect_id, outline="white", width=3)

	def deselect_block(self, block):
		if block in self.selected_blocks:
			self.selected_blocks.remove(block)
			self.canvas.itemconfig(block.rect_id, outline="#222", width=2)

	def clear_selection(self):
		for block in list(self.selected_blocks):
			self.deselect_block(block)

	def build_topbar(self):
		self.topbar_frame = tk.Frame(self.root, bg="#1E2227", height=45)
		self.topbar_frame.pack(side="top", fill="x")
		self.topbar_frame.pack_propagate(False)
		tk.Button(self.topbar_frame, text="📂 LOAD", bg="#4DB6AC", fg="black", font=("Arial", 9, "bold"), command=self.load_project, relief="flat", padx=10).pack(side="left", padx=5, pady=8)
		tk.Button(self.topbar_frame, text="💾 SAVE", bg="#555", fg="white", font=("Arial", 9, "bold"), command=self.save_project, relief="flat", padx=5).pack(side="left", padx=5, pady=8)
		tk.Button(self.topbar_frame, text="💾 SAVE AS", bg="#555", fg="white", font=("Arial", 9, "bold"), command=self.save_as_project, relief="flat", padx=5).pack(side="left", padx=5, pady=8)
		tk.Button(self.topbar_frame, text="↩️ UNDO", bg="#444", fg="white", font=("Arial", 9, "bold"), command=self.undo, relief="flat", padx=10).pack(side="left", padx=5, pady=8)
		tk.Button(self.topbar_frame, text="↪️ REDO", bg="#444", fg="white", font=("Arial", 9, "bold"), command=self.redo, relief="flat", padx=10).pack(side="left", padx=5, pady=8)
		tk.Button(self.topbar_frame, text="📝 STICKY NOTE", bg="#FFF59D", fg="black", font=("Arial", 9, "bold"), command=self.spawn_comment, relief="flat", padx=10).pack(side="left", padx=5, pady=8)
		self.snap_btn = tk.Button(self.topbar_frame, text="📐 SNAP: ON", bg="#4DD0E1", fg="black", font=("Arial", 9, "bold"), command=self.toggle_snap, relief="flat", padx=10)
		self.snap_btn.pack(side="left", padx=5, pady=8)
		tk.Button(self.topbar_frame, text="🗑 CLEAR", bg="#E57373", fg="black", font=("Arial", 9, "bold"), command=self.clear_workspace, relief="flat", padx=10).pack(side="left", padx=5, pady=8)
		tk.Button(self.topbar_frame, text="▶ COMPILE", bg="#A2D149", fg="black", font=("Arial", 10, "bold"), command=self.compile_script, relief="flat", padx=10).pack(side="right", padx=10, pady=8)
		tk.Button(self.topbar_frame, text="⚙️ OUT DIR", bg="#BA68C8", fg="black", font=("Arial", 9, "bold"), command=self.set_compile_path, relief="flat", padx=10).pack(side="right", padx=5, pady=8)

	def toggle_snap(self):
		self.snap_enabled = not self.snap_enabled
		self.snap_btn.config(text="📐 SNAP: ON" if self.snap_enabled else "📐 SNAP: OFF", bg="#4DD0E1" if self.snap_enabled else "#9E9E9E")

	def build_toolbox(self):
		t_canvas = tk.Canvas(self.toolbox_tab, bg="#333", highlightthickness=0)
		t_scroll = tk.Scrollbar(self.toolbox_tab, orient="vertical", command=t_canvas.yview)
		self.t_frame = tk.Frame(t_canvas, bg="#333")
		t_frame_id = t_canvas.create_window((0, 0), window=self.t_frame, anchor="nw")
		t_canvas.configure(yscrollcommand=t_scroll.set)
		def on_cfg(e):
			t_canvas.configure(scrollregion=t_canvas.bbox("all"))
			t_canvas.itemconfig(t_frame_id, width=e.width)
		t_canvas.bind("<Configure>", on_cfg)
		t_scroll.pack(side="right", fill="y")
		t_canvas.pack(side="left", fill="both", expand=True)
		toolbox_data = {
			"Core": [("PUSH", True), ("DUP", False),("CALL", True),("RET", False)],
			"Control Flow": [("LABEL", True), ("JMP", True), ("JZ", True)],
			"Math & Logic": [("ADD", False), ("SUB", False), ("MUL", False), ("DIV", False), ("MOD", False), ("CMP_EQ", False),("CMP_LT", False),("CMP_GT", False),("AND", False),("OR", False),("NOT", False)],
			"Hardware I/O": [("READ_GPIO", False), ("MODULATE", False)],
			"UI & Debug": [("DEBUG_PRINT", False), ("CREATE_BTN", False), ("SET_TEXT", False), ("PRINT_STR", False)],
			"System": [("HALT", False),("STORE", True),("LOAD", True),("PEEK", False), ("POKE", False)]
		}
		for category, ops in toolbox_data.items():
			tk.Label(self.t_frame, text=category, bg="#333", fg="#AAA", font=("Arial", 10, "bold"), pady=5).pack(anchor="w", padx=10)
			for opcode, has_input in ops:
				btn = tk.Button(self.t_frame, text=opcode, command=lambda o=opcode, c=category.split(" ")[0], i=has_input: self.spawn_block(o, c, i), bg="#555", fg="white", font=("Consolas", 9), relief="flat")
				btn.pack(fill="x", padx=10, pady=2)

	def build_data_manager(self):
		tk.Label(self.data_tab, text="Define Constants", bg="#333", fg="white", font=("Arial", 11, "bold"), pady=10).pack()
		tk.Label(self.data_tab, text="Label (Variable Name):", bg="#333", fg="#AAA").pack(anchor="w", padx=10)
		self.data_label_entry = tk.Entry(self.data_tab, bg="#444", fg="white", insertbackground="white")
		self.data_label_entry.pack(fill="x", padx=10, pady=5)
		tk.Label(self.data_tab, text="Value (String Content):", bg="#333", fg="#AAA").pack(anchor="w", padx=10)
		self.data_val_entry = tk.Entry(self.data_tab, bg="#444", fg="white", insertbackground="white")
		self.data_val_entry.pack(fill="x", padx=10, pady=5)
		tk.Button(self.data_tab, text="Add to .DATA", command=self.add_data_entry, bg="#4DB6AC").pack(pady=10)
		self.data_listbox = tk.Listbox(self.data_tab, bg="#222", fg="#A2D149", font=("Consolas", 10))
		self.data_listbox.pack(fill="both", expand=True, padx=10, pady=5)
		tk.Button(self.data_tab, text="Remove Selected", command=self.remove_data_entry, bg="#E57373").pack(pady=5)

	def redraw_grid(self):
		self.canvas.delete("grid_line")
		w = self.canvas.winfo_width()
		h = self.canvas.winfo_height()
		if w <= 1 or h <= 1: return
		z = self.zoom_level
		step = 20 * z 
		if step < 5: return 
		x0 = self.canvas.canvasx(0)
		y0 = self.canvas.canvasy(0)
		x1 = self.canvas.canvasx(w)
		y1 = self.canvas.canvasy(h)
		curr_x = x0 - (x0 % step)
		while curr_x < x1:
			self.canvas.create_line(curr_x, y0, curr_x, y1, fill="#333740", tags="grid_line")
			curr_x += step
		curr_y = y0 - (y0 % step)
		while curr_y < y1:
			self.canvas.create_line(x0, curr_y, x1, curr_y, fill="#333740", tags="grid_line")
			curr_y += step
		self.canvas.tag_lower("grid_line")

	def add_data_entry(self):
		lbl = self.data_label_entry.get().strip()
		val = self.data_val_entry.get().strip()
		if lbl and val:
			self.data_entries[lbl] = val
			self.refresh_data_list()
			self.data_label_entry.delete(0, tk.END)
			self.data_val_entry.delete(0, tk.END)
			self.save_history_state()

	def remove_data_entry(self):
		selection = self.data_listbox.curselection()
		if selection:
			item = self.data_listbox.get(selection[0])
			lbl = item.split(":")[0].strip()
			if lbl in self.data_entries:
				del self.data_entries[lbl]
				self.refresh_data_list()
				self.save_history_state()

	def refresh_data_list(self):
		self.data_listbox.delete(0, tk.END)
		for lbl, val in self.data_entries.items():
			self.data_listbox.insert(tk.END, f"{lbl} : \"{val}\"")

	def save_project(self):
		if not self.blocks and not self.data_entries and not self.comments:
			messagebox.showwarning("Empty", "Workspace is empty. Nothing to save!")
			return
		if self.current_filepath:
			self._write_save_file(self.current_filepath)
		else:
			self.save_as_project()

	def save_as_project(self):
		if not self.blocks and not self.data_entries and not self.comments:
			messagebox.showwarning("Empty", "Workspace is empty. Nothing to save!")
			return
		filepath = filedialog.asksaveasfilename(defaultextension=".cvmv", filetypes=[("CVM Visual Source", "*.cvmv"), ("All Files", "*.*")], title="Save Project As")
		if not filepath: return
		self.current_filepath = filepath
		self._write_save_file(filepath)

	def _write_save_file(self, filepath):
		project_data = {
			"camera": {
				"zoom_level": self.zoom_level,
				"xview": self.canvas.xview()[0],
				"yview": self.canvas.yview()[0]
			},
			"data_entries": self.data_entries,
			"blocks": [b.get_state() for b in self.blocks],
			"comments": [c.get_state() for c in self.comments]
		}
		try:
			with open(filepath, "w") as f:
				json.dump(project_data, f, indent=4)
			messagebox.showinfo("Success", "Project saved successfully!")
		except Exception as e:
			messagebox.showerror("Error", f"Failed to save project: {e}")

	def load_project(self):
		if self.blocks or self.data_entries or self.comments:
			if not messagebox.askyesno("Warning", "Loading a project will replace your current workspace.\n\nContinue?"):
				return
		filepath = filedialog.askopenfilename(filetypes=[("CVM Project Files", "*.cvmv"), ("All Files", "*.*")], title="Open Project")
		if not filepath: return
		self.current_filepath = filepath
		try:
			with open(filepath, "r") as f:
				project_data = json.load(f)
		except Exception as e:
			messagebox.showerror("Error", f"Failed to load project: {e}")
			return
		self.apply_workspace_state(project_data)
		camera = project_data.get("camera", {"zoom_level": 1.0, "xview": 0.5, "yview": 0.5})
		self.root.update_idletasks()
		self.canvas.xview_moveto(camera.get("xview", 0.5))
		self.canvas.yview_moveto(camera.get("yview", 0.5))
		self.save_history_state()
		messagebox.showinfo("Success", "Project loaded successfully!")

	def spawn_block(self, opcode, category, has_input):
		offset = (len(self.blocks) % 10) * 10
		screen_cx = self.canvas.winfo_width() / 2
		screen_cy = self.canvas.winfo_height() / 2
		if screen_cx <= 1: screen_cx = 200
		if screen_cy <= 1: screen_cy = 200
		cx = self.canvas.canvasx(screen_cx + offset)
		cy = self.canvas.canvasy(screen_cy + offset)
		if self.snap_enabled:
			step = 20 * self.zoom_level
			cx = round(cx / step) * step
			cy = round(cy / step) * step
		new_block = DraggableBlock(self, cx, cy, opcode, category, has_input)
		self.blocks.append(new_block)
		self.update_connections()
		self.save_history_state()

	def spawn_comment(self):
		offset = (len(self.comments) % 10) * 10
		screen_cx = self.canvas.winfo_width() / 2
		screen_cy = self.canvas.winfo_height() / 2
		if screen_cx <= 1: screen_cx = 200
		if screen_cy <= 1: screen_cy = 200
		cx = self.canvas.canvasx(screen_cx + offset)
		cy = self.canvas.canvasy(screen_cy + offset)
		if self.snap_enabled:
			step = 20 * self.zoom_level
			cx = round(cx / step) * step
			cy = round(cy / step) * step
		new_comment = DraggableCommentBox(self, cx, cy)
		self.comments.append(new_comment)
		self.save_history_state()

	def force_clear_workspace(self):
		for b in list(self.blocks): b.delete_self(None)
		for c in list(self.comments): c.delete_self(None)
		self.blocks.clear()
		self.comments.clear()
		self.selected_blocks.clear()
		self.data_entries.clear()
		self.canvas.delete("connection")
		self.canvas.delete("sel_rect")
		self.refresh_data_list()
		self.update_connections()
		self.redraw_grid()

	def clear_workspace(self):
		if messagebox.askyesno("Clear", "Delete all blocks, comments, and data?"):
			self.force_clear_workspace()
			self.save_history_state()

	def update_connections(self):
		self.canvas.delete("connection")
		if not self.blocks: return
		sorted_b = sorted(self.blocks, key=lambda b: b.get_y_position())
		for i in range(len(sorted_b) - 1):
			b1, b2 = sorted_b[i], sorted_b[i+1]
			c1, c2 = self.canvas.coords(b1.rect_id), self.canvas.coords(b2.rect_id)
			self.canvas.create_line((c1[0]+c1[2])/2, c1[3], (c2[0]+c2[2])/2, c2[1], arrow=tk.LAST, fill="#666", width=2, tags="connection")
		labels = {b.entry.get(): b for b in self.blocks if b.opcode == "LABEL" and b.has_input}
		for b in self.blocks:
			if b.opcode in ["JMP", "JZ"] and b.has_input:
				target = labels.get(b.entry.get())
				if target:
					c1, c2 = self.canvas.coords(b.rect_id), self.canvas.coords(target.rect_id)
					px = max(c1[2], c2[2]) + 60
					self.canvas.create_line(c1[2], (c1[1]+c1[3])/2, px, (c1[1]+c1[3])/2, px, (c2[1]+c2[3])/2, c2[2], (c2[1]+c2[3])/2, arrow=tk.LAST, fill="#FFB74D", width=2, dash=(5, 5), tags="connection")
		self.canvas.tag_lower("connection")
		self.canvas.tag_lower("grid_line") 

	def set_compile_path(self):
		filepath = filedialog.asksaveasfilename(defaultextension=".cvms", filetypes=[("CVM Assembly", "*.cvms"), ("All Files", "*.*")], title="Set Compile Output Path")
		if filepath:
			self.compile_filepath = filepath
			messagebox.showinfo("Path Set", f"Output path set to:\n{filepath}")

	def compile_script(self):
		if not self.blocks: return
		out_path = self.compile_filepath
		if not out_path:
			if self.current_filepath:
				out_path = os.path.splitext(self.current_filepath)[0] + ".cvms"
			else:
				out_path = filedialog.asksaveasfilename(defaultextension=".cvms", filetypes=[("CVM Assembly Source", "*.cvms"), ("All Files", "*.*")], title="Compile Project As")
				if not out_path: return
				self.compile_filepath = out_path
		data_code = ".DATA\n"
		for lbl, val in self.data_entries.items():
			data_code += f"{lbl}: \"{val}\"\n"
		sorted_b = sorted(self.blocks, key=lambda b: b.get_y_position())
		code_section = ".CODE\n"
		for b in sorted_b:
			code_section += b.get_code() + "\n"
		full_output = data_code + "\n" + code_section
		compiled_filename = os.path.basename(out_path)
		try:
			with open(out_path, "w") as f:
				f.write(full_output)
			messagebox.showinfo("Compiled", f"Successfully compiled to: {compiled_filename}")
		except Exception as e:
			messagebox.showerror("Error", str(e))

if __name__ == "__main__":
	root = tk.Tk()
	app = VisualAssemblyEditor(root)
	root.mainloop()

import json
import os
import re
import tkinter as tk
from collections import OrderedDict
from tkinter import filedialog, messagebox, ttk

DESCRIPTION_MAP = {
    "engine": "Данные двигателя (мощность, крутящий момент и прочие параметры)",
    "mass": "Масса автомобиля в килограммах",
    "slotType": "Тип слота для комплектующих",
    "information": "Информация об автомобиле",
    "nodes": "Список узлов (масса, координаты, теги)",
    "beams": "Связи между узлами (жесткость, демпфирование)",
    "triangles": "Треугольники для визуализации/коллизии",
    "hydros": "Гидравлические элементы",
    "flexbodies": "Список гибких кузовных элементов",
}


def strip_comments_and_trailing_commas(text: str) -> str:
    text = re.sub(r"//.*?$", "", text, flags=re.MULTILINE)
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


def load_jbeam(path: str) -> OrderedDict:
    with open(path, "r", encoding="utf-8") as handle:
        raw = handle.read()
    cleaned = strip_comments_and_trailing_commas(raw)
    return json.loads(cleaned, object_pairs_hook=OrderedDict)


def dump_value(value: object) -> str:
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return "" if value is None else str(value)


def parse_value(original: object, text: str) -> object:
    if isinstance(original, (dict, list)):
        return json.loads(text)
    if isinstance(original, bool):
        lowered = text.strip().lower()
        if lowered in {"true", "1", "да", "yes"}:
            return True
        if lowered in {"false", "0", "нет", "no"}:
            return False
        raise ValueError("Ожидается логическое значение (true/false)")
    if isinstance(original, int):
        return int(text)
    if isinstance(original, float):
        return float(text)
    return text


class Tooltip:
    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip: tk.Toplevel | None = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)
        widget.bind("<Motion>", self.move)

    def show(self, event: tk.Event) -> None:
        if self.tip or not self.text:
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.attributes("-topmost", True)
        label = tk.Label(
            self.tip,
            text=self.text,
            justify="left",
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            padx=6,
            pady=4,
            wraplength=320,
        )
        label.pack()
        self.move(event)

    def move(self, event: tk.Event) -> None:
        if not self.tip:
            return
        x = event.x_root + 16
        y = event.y_root + 12
        self.tip.geometry(f"+{x}+{y}")

    def hide(self, _event: tk.Event) -> None:
        if self.tip:
            self.tip.destroy()
            self.tip = None


class ScrollableFrame(ttk.Frame):
    def __init__(self, master: tk.Widget) -> None:
        super().__init__(master)
        self.canvas = tk.Canvas(self, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.container = ttk.Frame(self.canvas)
        self.container.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.window = self.canvas.create_window((0, 0), window=self.container, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfig(self.window, width=event.width),
        )


class JbeamEditor(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Редактор JBeam файлов")
        self.geometry("1000x700")

        self.folder_path = tk.StringVar()
        self.files: list[str] = []
        self.current_path: str | None = None
        self.current_data: OrderedDict | None = None
        self.value_widgets: dict[str, tk.Widget] = {}

        self.create_widgets()

    def create_widgets(self) -> None:
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(top_frame, text="Папка с JBeam:").pack(side="left")
        ttk.Entry(top_frame, textvariable=self.folder_path, width=60).pack(
            side="left", padx=5
        )
        ttk.Button(top_frame, text="Выбрать...", command=self.choose_folder).pack(
            side="left"
        )

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="y")

        ttk.Label(left_frame, text="Файлы JBeam").pack(anchor="w")
        self.file_list = tk.Listbox(left_frame, width=40, height=25)
        self.file_list.pack(fill="y", expand=True)
        self.file_list.bind("<<ListboxSelect>>", self.on_select_file)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="left", fill="both", expand=True, padx=(10, 0))

        self.scrollable = ScrollableFrame(right_frame)
        self.scrollable.pack(fill="both", expand=True)

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill="x", padx=10, pady=10)
        ttk.Button(bottom_frame, text="Сохранить", command=self.save_file).pack(
            side="right"
        )

    def choose_folder(self) -> None:
        path = filedialog.askdirectory()
        if not path:
            return
        self.folder_path.set(path)
        self.load_file_list(path)

    def load_file_list(self, folder: str) -> None:
        self.file_list.delete(0, tk.END)
        self.files = []
        for root, _dirs, filenames in os.walk(folder):
            for name in filenames:
                if name.lower().endswith(".jbeam"):
                    full_path = os.path.join(root, name)
                    rel_path = os.path.relpath(full_path, folder)
                    self.files.append(full_path)
                    self.file_list.insert(tk.END, rel_path)
        if not self.files:
            messagebox.showinfo("Нет файлов", "В выбранной папке нет файлов .jbeam")

    def on_select_file(self, _event: tk.Event) -> None:
        selection = self.file_list.curselection()
        if not selection:
            return
        index = selection[0]
        path = self.files[index]
        self.load_file(path)

    def load_file(self, path: str) -> None:
        try:
            data = load_jbeam(path)
        except (OSError, json.JSONDecodeError) as exc:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл: {exc}")
            return

        self.current_path = path
        self.current_data = data
        self.render_form(data)

    def render_form(self, data: OrderedDict) -> None:
        for child in self.scrollable.container.winfo_children():
            child.destroy()
        self.value_widgets = {}

        for row, (key, value) in enumerate(data.items()):
            label = ttk.Label(self.scrollable.container, text=key)
            label.grid(row=row, column=0, sticky="nw", padx=5, pady=5)
            tooltip_text = DESCRIPTION_MAP.get(
                key, f"Параметр «{key}». Укажите значение для этого раздела."
            )
            Tooltip(label, tooltip_text)

            if isinstance(value, (dict, list)):
                entry = tk.Text(self.scrollable.container, height=6, wrap="word")
                entry.insert("1.0", dump_value(value))
                entry.grid(row=row, column=1, sticky="nsew", padx=5, pady=5)
                Tooltip(entry, tooltip_text)
            else:
                entry = ttk.Entry(self.scrollable.container)
                entry.insert(0, dump_value(value))
                entry.grid(row=row, column=1, sticky="ew", padx=5, pady=5)
                Tooltip(entry, tooltip_text)

            self.value_widgets[key] = entry

        self.scrollable.container.columnconfigure(1, weight=1)

    def save_file(self) -> None:
        if not self.current_path or self.current_data is None:
            messagebox.showwarning("Нет файла", "Сначала выберите файл для сохранения")
            return

        updated = OrderedDict()
        try:
            for key, original in self.current_data.items():
                widget = self.value_widgets[key]
                if isinstance(widget, tk.Text):
                    text = widget.get("1.0", "end").strip()
                else:
                    text = widget.get().strip()
                updated[key] = parse_value(original, text)
        except (ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Ошибка", f"Не удалось сохранить значения: {exc}")
            return

        try:
            with open(self.current_path, "w", encoding="utf-8") as handle:
                json.dump(updated, handle, ensure_ascii=False, indent=2)
            messagebox.showinfo("Сохранено", "Файл успешно сохранен")
        except OSError as exc:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {exc}")


if __name__ == "__main__":
    app = JbeamEditor()
    app.mainloop()

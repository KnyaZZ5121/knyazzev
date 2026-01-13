import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


COMMENT_RE = re.compile(r"//.*?$|/\*.*?\*/", re.MULTILINE | re.DOTALL)
TRAILING_COMMA_RE = re.compile(r",\s*([}\]])")

DEFAULT_TOOLTIPS = {
    "mass": "Масса детали/машины (кг).",
    "dragCoef": "Коэффициент аэродинамического сопротивления.",
    "frictionCoef": "Коэффициент трения.",
    "camber": "Развал колёс (градусы).",
    "toe": "Схождение колёс (градусы).",
    "spring": "Жёсткость пружины.",
    "damp": "Жёсткость амортизатора.",
}


def strip_json_comments(text: str) -> str:
    no_comments = COMMENT_RE.sub("", text)
    return TRAILING_COMMA_RE.sub(r"\1", no_comments)


class Tooltip:
    def __init__(self, widget: tk.Widget, text: str):
        self.widget = widget
        self.text = text
        self.tip = None
        self.widget.bind("<Enter>", self.show)
        self.widget.bind("<Leave>", self.hide)
        self.widget.bind("<Motion>", self.move)

    def show(self, _event=None):
        if self.tip or not self.text:
            return
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        label = tk.Label(
            self.tip,
            text=self.text,
            background="#ffffe0",
            relief="solid",
            borderwidth=1,
            font=("Segoe UI", 9),
            justify="left",
        )
        label.pack(ipadx=6, ipady=4)

    def move(self, event):
        if not self.tip:
            return
        x = event.x_root + 12
        y = event.y_root + 12
        self.tip.wm_geometry(f"+{x}+{y}")

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class JBeamEditor(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Редактор JBeam")
        self.geometry("1100x700")

        self.folder_path = tk.StringVar()
        self.current_file = None
        self.current_data = None
        self.field_widgets = {}
        self.tooltips = dict(DEFAULT_TOOLTIPS)
        self.load_default_tooltips()

        self.create_widgets()

    def create_widgets(self):
        top_frame = ttk.Frame(self)
        top_frame.pack(fill="x", padx=10, pady=10)

        ttk.Label(top_frame, text="Папка с JBeam:").pack(side="left")
        ttk.Entry(top_frame, textvariable=self.folder_path, width=60).pack(
            side="left", padx=6
        )
        ttk.Button(
            top_frame, text="Выбрать...", command=self.select_folder
        ).pack(side="left")
        ttk.Button(
            top_frame, text="Подсказки...", command=self.select_tooltips_file
        ).pack(side="left", padx=(6, 0))

        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="y")

        ttk.Label(left_frame, text="JBeam файлы").pack(anchor="w")
        self.files_listbox = tk.Listbox(left_frame, width=40, height=30)
        self.files_listbox.pack(fill="y", expand=True)
        self.files_listbox.bind("<<ListboxSelect>>", self.load_selected_file)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="left", fill="both", expand=True, padx=(10, 0))

        self.note_label = ttk.Label(
            right_frame,
            text=(
                "Выберите JBeam файл и отредактируйте значения. "
                "Комментарии будут удалены при сохранении. "
                "Подсказки можно загрузить из JSON файла."
            ),
            foreground="#555",
        )
        self.note_label.pack(anchor="w")

        self.canvas = tk.Canvas(right_frame)
        self.scrollbar = ttk.Scrollbar(
            right_frame, orient="vertical", command=self.canvas.yview
        )
        self.form_frame = ttk.Frame(self.canvas)

        self.form_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.create_window((0, 0), window=self.form_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(
            bottom_frame, text="Сохранить", command=self.save_current_file
        ).pack(side="right")

        self.status_var = tk.StringVar(value="Готово")
        ttk.Label(bottom_frame, textvariable=self.status_var).pack(side="left")

    def select_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.folder_path.set(folder)
        self.populate_files(folder)

    def populate_files(self, folder: str):
        self.files_listbox.delete(0, tk.END)
        for root, _dirs, files in os.walk(folder):
            for name in sorted(files):
                if name.lower().endswith(".jbeam"):
                    path = os.path.join(root, name)
                    rel_path = os.path.relpath(path, folder)
                    self.files_listbox.insert(tk.END, rel_path)
        self.status_var.set("Список файлов обновлён")

    def load_default_tooltips(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        default_path = os.path.join(base_dir, "tooltips_ru.json")
        if os.path.exists(default_path):
            self.load_tooltips_file(default_path, silent=True)

    def select_tooltips_file(self):
        path = filedialog.askopenfilename(
            title="Выберите файл подсказок",
            filetypes=(("JSON файлы", "*.json"), ("Все файлы", "*.*")),
        )
        if not path:
            return
        self.load_tooltips_file(path, silent=False)

    def load_tooltips_file(self, path: str, silent: bool = False):
        try:
            with open(path, "r", encoding="utf-8") as file:
                payload = json.load(file)
        except OSError as exc:
            if not silent:
                messagebox.showerror("Ошибка", f"Не удалось открыть файл.\n{exc}")
            return
        except json.JSONDecodeError as exc:
            if not silent:
                messagebox.showerror(
                    "Ошибка", f"Файл подсказок содержит некорректный JSON.\n{exc}"
                )
            return

        if not isinstance(payload, dict):
            if not silent:
                messagebox.showerror(
                    "Ошибка", "Файл подсказок должен содержать объект JSON."
                )
            return

        for key, value in payload.items():
            if isinstance(value, str):
                self.tooltips[key] = value

        if self.current_data is not None:
            self.build_form(self.current_data)

        if not silent:
            self.status_var.set("Подсказки обновлены")

    def load_selected_file(self, _event=None):
        selection = self.files_listbox.curselection()
        if not selection:
            return
        rel_path = self.files_listbox.get(selection[0])
        folder = self.folder_path.get()
        path = os.path.join(folder, rel_path)
        try:
            with open(path, "r", encoding="utf-8") as file:
                raw = file.read()
            data = json.loads(strip_json_comments(raw))
        except json.JSONDecodeError as exc:
            messagebox.showerror(
                "Ошибка",
                f"Не удалось разобрать файл.\n{exc}",
            )
            return
        except OSError as exc:
            messagebox.showerror("Ошибка", f"Не удалось открыть файл.\n{exc}")
            return

        self.current_file = path
        self.current_data = data
        self.build_form(data)
        self.status_var.set(f"Открыт файл: {rel_path}")

    def build_form(self, data: dict):
        for child in self.form_frame.winfo_children():
            child.destroy()
        self.field_widgets.clear()

        row = 0
        for key, value in data.items():
            label = ttk.Label(self.form_frame, text=key)
            label.grid(row=row, column=0, sticky="nw", padx=4, pady=4)

            tooltip_text = self.tooltips.get(
                key, f"Настройка: {key}. Подробное описание отсутствует."
            )

            if isinstance(value, (dict, list)):
                text_widget = tk.Text(self.form_frame, height=4, width=60)
                text_widget.insert("1.0", json.dumps(value, ensure_ascii=False, indent=2))
                text_widget.grid(row=row, column=1, sticky="we", padx=4, pady=4)
                self.field_widgets[key] = ("complex", text_widget)
                Tooltip(text_widget, tooltip_text)
            else:
                entry = ttk.Entry(self.form_frame, width=60)
                entry.insert(0, str(value))
                entry.grid(row=row, column=1, sticky="we", padx=4, pady=4)
                self.field_widgets[key] = ("simple", entry)
                Tooltip(entry, tooltip_text)

            row += 1

        self.form_frame.columnconfigure(1, weight=1)

    def save_current_file(self):
        if not self.current_file or self.current_data is None:
            messagebox.showwarning("Внимание", "Сначала выберите файл.")
            return

        updated = {}
        for key, (kind, widget) in self.field_widgets.items():
            if kind == "simple":
                raw_value = widget.get()
                updated[key] = self.coerce_value(raw_value)
            else:
                raw_text = widget.get("1.0", tk.END).strip()
                try:
                    updated[key] = json.loads(raw_text) if raw_text else None
                except json.JSONDecodeError as exc:
                    messagebox.showerror(
                        "Ошибка",
                        f"Поле '{key}' содержит некорректный JSON.\n{exc}",
                    )
                    return

        try:
            with open(self.current_file, "w", encoding="utf-8") as file:
                json.dump(updated, file, ensure_ascii=False, indent=2)
        except OSError as exc:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл.\n{exc}")
            return

        self.current_data = updated
        self.status_var.set("Файл сохранён")
        messagebox.showinfo("Готово", "Файл успешно сохранён.")

    @staticmethod
    def coerce_value(raw_value: str):
        value = raw_value.strip()
        if value.lower() in {"true", "false"}:
            return value.lower() == "true"
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            return value


if __name__ == "__main__":
    app = JBeamEditor()
    app.mainloop()

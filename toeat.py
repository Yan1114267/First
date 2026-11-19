"""
待办清单 —— Python + tkinter 桌面应用

功能：
  - 添加 / 删除 / 完成待办
  - 每条待办可设置截止日期
  - 已完成的待办仍然显示，灰色 + 删除线
  - 逾期未完成标红，临近截止标橙
  - 数据保存在同目录 tasks.json

运行：python toeat.py
"""

import json
import os
import sys
from datetime import date, datetime
import tkinter as tk
from tkinter import messagebox, ttk
from tkinter import font as tkfont

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "tasks.json")


class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("吃什么好呢")
        self.root.geometry("560x580")
        self.root.minsize(480, 440)

        self.tasks = self.load_tasks()   # [{"text": str, "done": bool, "due": "YYYY-MM-DD"|None}]
        self.build_ui()
        self.refresh()

    # ==================== 界面 ====================
    def build_ui(self):
        tk.Label(self.root, text="吃什么好",
                 font=("Microsoft YaHei UI", 18, "bold")).pack(pady=(16, 10))

        # ---- 输入行：任务文字 + 截止日期 + 添加 ----
        input_row = tk.Frame(self.root)
        input_row.pack(fill="x", padx=18)

        self.entry = tk.Entry(input_row, font=("Microsoft YaHei UI", 12))
        self.entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.entry.bind("<Return>", self.on_enter)

        self.due_entry = tk.Entry(input_row, font=("Microsoft YaHei UI", 11),
                                  width=12, justify="center")
        self.due_entry.pack(side="left", padx=(8, 0), ipady=5)
        self.due_entry.bind("<Return>", self.on_enter)

        tk.Button(input_row, text="添加", width=6,
                  font=("Microsoft YaHei UI", 11),
                  command=self.add_task).pack(side="left", padx=(8, 0))

        tk.Label(self.root, text="截止日期格式：2026-12-31 或 12-31（可留空）",
                 font=("Microsoft YaHei UI", 9), fg="#888888",
                 anchor="w").pack(fill="x", padx=20, pady=(4, 0))

        # ---- 列表区：Treeview ----
        list_row = tk.Frame(self.root)
        list_row.pack(fill="both", expand=True, padx=18, pady=12)

        style = ttk.Style()
        style.configure("Todo.Treeview",
                        font=("Microsoft YaHei UI", 11), rowheight=30)
        style.configure("Todo.Treeview.Heading",
                        font=("Microsoft YaHei UI", 10, "bold"))

        scrollbar = tk.Scrollbar(list_row)
        scrollbar.pack(side="right", fill="y")

        self.tree = ttk.Treeview(list_row, columns=("text", "due"),
                                 show="headings", selectmode="extended",
                                 style="Todo.Treeview",
                                 yscrollcommand=scrollbar.set)
        self.tree.heading("text", text="待吃")
        self.tree.heading("due", text="日期")
        self.tree.column("text", anchor="w", width=300, stretch=True)
        self.tree.column("due", anchor="center", width=120, stretch=False)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.tree.yview)

        # Treeview 的"删除线"只能靠字体实现
        self.font_done = tkfont.Font(family="Microsoft YaHei UI", size=11,
                                     overstrike=True)
        # 标签 = 一组的样式，插入行时挂上去
        self.tree.tag_configure("done", foreground="#b0b0b0", font=self.font_done)
        self.tree.tag_configure("overdue", foreground="#c0392b")
        self.tree.tag_configure("soon", foreground="#d35400")

        self.tree.bind("<Double-Button-1>", lambda e: self.toggle_done())
        self.tree.bind("<Delete>", lambda e: self.delete_selected())

        # ---- 按钮行 ----
        btn_row = tk.Frame(self.root)
        btn_row.pack(fill="x", padx=18)

        for text, cmd in (("完成 / 取消", self.toggle_done),
                          ("设置日期", self.set_due),
                          ("删除", self.delete_selected),
                          ("清除已吃", self.clear_done),
                          ("全部吃了", self.complete_all)):
            tk.Button(btn_row, text=text, font=("Microsoft YaHei UI", 10),
                      command=cmd).pack(side="left", padx=(0, 6))

        # ---- 状态栏 ----
        self.status = tk.Label(self.root, text="", anchor="w",
                               font=("Microsoft YaHei UI", 9), fg="#666666")
        self.status.pack(fill="x", padx=18, pady=(10, 14))

    # ==================== 数据 → 界面 ====================
    def refresh(self):
        """清空并重画整个列表。数据变了就调用一次。"""
        self.tree.delete(*self.tree.get_children())
        today = date.today()
        overdue = 0

        for i, task in enumerate(self.tasks):
            due = self.parse_due_value(task.get("due"))
            due_text, state = self.describe_due(due, today)

            if state == "overdue" and not task["done"]:
                overdue += 1

            if task["done"]:
                tags = ("done",)              # 已完成：灰色 + 删除线
            elif state in ("overdue", "soon"):
                tags = (state,)
            else:
                tags = ()

            self.tree.insert("", "end", iid=str(i),
                             values=(task["text"], due_text), tags=tags)

        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t["done"])
        self.status.config(text=f"共 {total} 条 · 已完成 {done} 条 · 逾期 {overdue} 条")

    # ==================== 日期处理 ====================
    def parse_due_input(self, text):
        """把用户输入的字符串解析成 date。空串返回 None；格式不对抛 ValueError。"""
        text = text.strip()
        if not text:
            return None

        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m-%d", "%m/%d"):
            try:
                d = datetime.strptime(text, fmt).date()
            except ValueError:
                continue
            if fmt in ("%m-%d", "%m/%d"):        # 只写了月日 → 补今年
                d = d.replace(year=date.today().year)
            return d

        raise ValueError(text)

    @staticmethod
    def parse_due_value(value):
        """从 JSON 里读出来的字符串 → date（坏数据当 None）。"""
        if not value:
            return None
        try:
            return datetime.strptime(str(value), "%Y-%m-%d").date()
        except ValueError:
            return None

    @staticmethod
    def describe_due(due, today):
        """返回 (显示文字, 状态)。状态用于决定颜色标签。"""
        if due is None:
            return "—", "none"

        days = (due - today).days
        if days < 0:
            return f"{due:%m-%d} 逾期{-days}天", "overdue"
        if days == 0:
            return "今天", "soon"
        if days == 1:
            return "明天", "soon"
        if days <= 3:
            return f"{due:%m-%d} · {days}天后", "soon"
        if due.year != today.year:
            return f"{due:%Y-%m-%d}", "normal"
        return f"{due:%m-%d}", "normal"

    # ==================== 操作 ====================
    def on_enter(self, event):
        self.add_task()
        return "break"

    def add_task(self):
        text = self.entry.get().strip()
        if not text:
            return
        try:
            due = self.parse_due_input(self.due_entry.get())
        except ValueError:
            messagebox.showerror("日期格式有误",
                                 "请写成 2026-12-31 或 12-31 这样的格式，\n或者留空不填喵～")
            return

        self.tasks.append({
            "text": text,
            "done": False,
            "due": due.isoformat() if due else None,
        })
        self.entry.delete(0, "end")
        self.due_entry.delete(0, "end")
        self.save_tasks()
        self.refresh()
        self.entry.focus_set()

    def toggle_done(self):
        selected = self.tree.selection()
        if not selected:
            return
        for iid in selected:
            task = self.tasks[int(iid)]
            task["done"] = not task["done"]
        self.save_tasks()
        self.refresh()

    def set_due(self):
        """把输入框里的日期应用到选中的待办上。"""
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("提示", "先在列表里选中要设置日期的待办哦～")
            return
        try:
            due = self.parse_due_input(self.due_entry.get())
        except ValueError:
            messagebox.showerror("日期格式有误",
                                 "请写成 2026-12-31 或 12-31 这样的格式")
            return

        for iid in selected:
            self.tasks[int(iid)]["due"] = due.isoformat() if due else None
        self.save_tasks()
        self.refresh()

    def delete_selected(self):
        selected = sorted((int(i) for i in self.tree.selection()), reverse=True)
        if not selected:
            messagebox.showinfo("提示", "先选中要删除的条目哦～")
            return
        for i in selected:          # 倒序删，避免索引错位
            del self.tasks[i]
        self.save_tasks()
        self.refresh()

    def clear_done(self):
        if not any(t["done"] for t in self.tasks):
            return
        if not messagebox.askyesno("确认", "确定要清除所有已完成的待办吗？"):
            return
        self.tasks = [t for t in self.tasks if not t["done"]]
        self.save_tasks()
        self.refresh()

    def complete_all(self):
        for task in self.tasks:
            task["done"] = True
        self.save_tasks()
        self.refresh()

    # ==================== 持久化 ====================
    def load_tasks(self):
        if not os.path.exists(DATA_FILE):
            return []
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        tasks = []
        for item in data:
            if not isinstance(item, dict) or not item.get("text"):
                continue
            raw_due = item.get("due")
            due = None
            if raw_due:
                try:
                    due = datetime.strptime(str(raw_due), "%Y-%m-%d").date().isoformat()
                except ValueError:
                    due = None
            tasks.append({"text": str(item["text"]),
                          "done": bool(item.get("done")),
                          "due": due})
        return tasks

    def save_tasks(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except OSError as e:
            messagebox.showerror("保存失败", f"无法写入：\n{DATA_FILE}\n\n{e}")


def main():
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    TodoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

"""
待办清单 —— Python + tkinter 桌面应用

运行方式：
    python todo.py

数据保存在同目录的 tasks.json 里，关掉程序也不会丢。
"""

import json
import os
import sys
import tkinter as tk
from tkinter import messagebox

# 当前文件所在目录。用绝对路径，这样从任何地方运行都能找到数据文件
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(APP_DIR, "tasks.json")


class TodoApp:
    """整个应用。一个类，持有界面控件和任务数据。"""

    def __init__(self, root):
        self.root = root
        self.root.title("吃什么呢~？")
        self.root.geometry("440x560")
        self.root.minsize(380, 420)

        self.tasks = self.load_tasks()   # list[dict]：{"text": str, "done": bool}
        self.build_ui()
        self.refresh()

    # ==================== 界面 ====================
    def build_ui(self):
        """搭建所有控件。控件一旦创建就常驻，之后只更新它们的内容。"""

        # 标题
        tk.Label(self.root, text="我的待办清单",
                 font=("Microsoft YaHei UI", 18, "bold")).pack(pady=(18, 10))

        # 输入行：输入框 + 添加按钮
        input_row = tk.Frame(self.root)
        input_row.pack(fill="x", padx=18)

        self.entry = tk.Entry(input_row, font=("Microsoft YaHei UI", 12))
        self.entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.entry.bind("<Return>", self.on_enter)      # 回车也能添加

        tk.Button(input_row, text="添加", width=6,
                  font=("Microsoft YaHei UI", 11),
                  command=self.add_task).pack(side="left", padx=(8, 0))

        # 列表区：Listbox + 滚动条
        list_row = tk.Frame(self.root)
        list_row.pack(fill="both", expand=True, padx=18, pady=12)

        scrollbar = tk.Scrollbar(list_row)
        scrollbar.pack(side="right", fill="y")

        self.listbox = tk.Listbox(list_row,
                                  font=("Microsoft YaHei UI", 12),
                                  yscrollcommand=scrollbar.set,
                                  selectmode="extended",   # 支持 Ctrl/Shift 多选
                                  activestyle="none")
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)

        self.listbox.bind("<Double-Button-1>", lambda e: self.toggle_done())
        self.listbox.bind("<Delete>", lambda e: self.delete_selected())

        # 底部按钮行
        btn_row = tk.Frame(self.root)
        btn_row.pack(fill="x", padx=18)

        for text, cmd in (("完成 / 取消", self.toggle_done),
                          ("删除", self.delete_selected),
                          ("清除已吃掉", self.clear_done),
                          ("全部吃了", self.complete_all)):
            tk.Button(btn_row, text=text, font=("Microsoft YaHei UI", 10),
                      command=cmd).pack(side="left", padx=(0, 8))

        # 状态栏
        self.status = tk.Label(self.root, text="", anchor="w",
                               font=("Microsoft YaHei UI", 9), fg="#666666")
        self.status.pack(fill="x", padx=18, pady=(10, 14))

    # ==================== 数据 → 界面 ====================
    def refresh(self):
        """把 self.tasks 的内容重新画到 Listbox 上。

        每次数据变化都先清空再重画，简单可靠（数据量小，不心疼）。
        """
        self.listbox.delete(0, "end")
        for i, task in enumerate(self.tasks):
            prefix = "✓ " if task["done"] else "○ "
            self.listbox.insert("end", prefix + task["text"])
            if task["done"]:
                self.listbox.itemconfig(i, fg="#FEFEFE")   # 已完成的变白

        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t["done"])
        self.status.config(text=f"共 {total} 条 · 已完成 {done} 条")

    # ==================== 操作 ====================
    def on_enter(self, event):
        self.add_task()
        return "break"        # 阻止默认行为（避免响一声）

    def add_task(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.tasks.append({"text": text, "done": False})
        self.entry.delete(0, "end")
        self.save_tasks()
        self.refresh()
        self.listbox.see("end")     # 滚动到最后一行

    def toggle_done(self):
        """双击或按钮：把选中任务在 完成 / 未完成 之间切换。"""
        selected = self.listbox.curselection()
        if not selected:
            return
        for i in selected:
            self.tasks[i]["done"] = not self.tasks[i]["done"]
        self.save_tasks()
        self.refresh()

    def delete_selected(self):
        selected = sorted(self.listbox.curselection(), reverse=True)
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
        """启动时读取 tasks.json；文件不存在或损坏就当作空列表。"""
        if not os.path.exists(DATA_FILE):
            return []
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        return [{"text": str(t.get("text", "")), "done": bool(t.get("done"))}
                for t in data if isinstance(t, dict) and t.get("text")]

    def save_tasks(self):
        """每次数据变化后写回磁盘。"""
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, ensure_ascii=False, indent=2)
        except OSError as e:
            messagebox.showerror("保存失败", f"无法写入：\n{DATA_FILE}\n\n{e}")


def main():
    # Windows 高分屏下让文字不发虚
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    root = tk.Tk()
    TodoApp(root)
    root.mainloop()      # 进入事件循环：程序在这里"等"用户操作


if __name__ == "__main__":
    main()

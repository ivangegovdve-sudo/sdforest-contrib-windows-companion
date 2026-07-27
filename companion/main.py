"""SDForest Contribution Tool — tkinter GUI entry point."""
import json
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from companion.config import load_config, save_config
from companion.llamaparse import ParseError, ParseUnavailable, parse_pdf
from companion.gateway import GatewayError, submit_parsed_paper, check_status

_TARGET_OS_OPTIONS = [
    "Hypertrophy OS (hypertrophy)",
    "Women's Health OS (womens)",
]
_TARGET_OS_MAP = {label: label.split("(")[-1].rstrip(")") for label in _TARGET_OS_OPTIONS}


def _os_label_for(key: str) -> str:
    for label, k in _TARGET_OS_MAP.items():
        if k == key:
            return label
    return _TARGET_OS_OPTIONS[0]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SDForest Contribution Tool")
        self.geometry("580x480")
        self.resizable(False, False)

        self._cfg = load_config()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=8, pady=8)

        self._tab_submit = ttk.Frame(nb)
        self._tab_status = ttk.Frame(nb)
        nb.add(self._tab_submit, text="Submit Paper")
        nb.add(self._tab_status, text="Check Status")

        self._build_submit_tab(self._tab_submit)
        self._build_status_tab(self._tab_status)

    def _lbl(self, parent, text, row, col=0, sticky="w", **kw):
        ttk.Label(parent, text=text, **kw).grid(row=row, column=col, sticky=sticky, padx=6, pady=3)

    def _build_submit_tab(self, frame):
        frame.columnconfigure(1, weight=1)

        # LlamaParse API Key
        self._lbl(frame, "LlamaParse API Key:", 0)
        self._key_var = tk.StringVar(value=self._cfg.get("llamaparse_api_key", ""))
        ttk.Entry(frame, textvariable=self._key_var, show="*", width=45).grid(
            row=0, column=1, columnspan=2, sticky="ew", padx=6, pady=3)

        # Gateway URL
        self._lbl(frame, "Gateway URL:", 1)
        self._url_var = tk.StringVar(value=self._cfg.get("gateway_url", ""))
        ttk.Entry(frame, textvariable=self._url_var, width=45).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=6, pady=3)

        # Target OS
        self._lbl(frame, "Target OS:", 2)
        self._os_var = tk.StringVar(value=_os_label_for(self._cfg.get("last_target_os", "hypertrophy")))
        ttk.Combobox(frame, textvariable=self._os_var, values=_TARGET_OS_OPTIONS,
                     state="readonly", width=35).grid(
            row=2, column=1, columnspan=2, sticky="w", padx=6, pady=3)

        # PDF File
        self._lbl(frame, "PDF File:", 3)
        self._pdf_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self._pdf_var, width=35).grid(
            row=3, column=1, sticky="ew", padx=6, pady=3)
        ttk.Button(frame, text="Browse...", command=self._browse_pdf).grid(
            row=3, column=2, padx=4, pady=3)

        # Submit button
        self._submit_btn = ttk.Button(frame, text="Submit Paper", command=self._on_submit)
        self._submit_btn.grid(row=4, column=0, columnspan=3, sticky="ew", padx=6, pady=8, ipady=6)

        # Progress label
        self._progress_var = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self._progress_var, foreground="gray").grid(
            row=5, column=0, columnspan=3, sticky="w", padx=6)

        # Receipt ID row
        self._lbl(frame, "Receipt ID:", 6)
        self._receipt_var = tk.StringVar()
        receipt_entry = ttk.Entry(frame, textvariable=self._receipt_var, state="readonly", width=35)
        receipt_entry.grid(row=6, column=1, sticky="ew", padx=6, pady=3)
        ttk.Button(frame, text="Copy", command=lambda: self._copy_to_clipboard(self._receipt_var.get())).grid(
            row=6, column=2, padx=4, pady=3)

        # Error label
        self._error_var = tk.StringVar()
        self._error_lbl = ttk.Label(frame, textvariable=self._error_var, foreground="red",
                                    wraplength=530, justify="left")
        self._error_lbl.grid(row=7, column=0, columnspan=3, sticky="w", padx=6, pady=3)

    def _build_status_tab(self, frame):
        frame.columnconfigure(1, weight=1)

        self._lbl(frame, "Receipt ID:", 0)
        self._status_id_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self._status_id_var, width=40).grid(
            row=0, column=1, sticky="ew", padx=6, pady=3)

        ttk.Button(frame, text="Check Status", command=self._on_check_status).grid(
            row=0, column=2, padx=4, pady=3)

        self._status_text = tk.Text(frame, width=68, height=18, state="disabled",
                                    font=("Consolas", 10))
        self._status_text.grid(row=1, column=0, columnspan=3, padx=6, pady=6, sticky="nsew")
        frame.rowconfigure(1, weight=1)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse_pdf(self):
        path = filedialog.askopenfilename(
            title="Select a PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if path:
            self._pdf_var.set(path)

    def _copy_to_clipboard(self, text: str):
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)

    def _save_settings(self):
        self._cfg["llamaparse_api_key"] = self._key_var.get().strip()
        self._cfg["gateway_url"] = self._url_var.get().strip()
        self._cfg["last_target_os"] = _TARGET_OS_MAP.get(self._os_var.get(), "hypertrophy")
        save_config(self._cfg)

    def _set_progress(self, msg: str):
        self._progress_var.set(msg)
        self.update_idletasks()

    def _set_error(self, msg: str):
        self._error_var.set(msg)

    def _clear_error(self):
        self._error_var.set("")

    def _on_submit(self):
        self._clear_error()
        self._receipt_var.set("")

        api_key = self._key_var.get().strip()
        gateway_url = self._url_var.get().strip()
        target_os = _TARGET_OS_MAP.get(self._os_var.get(), "hypertrophy")
        pdf_path = self._pdf_var.get().strip()

        if not api_key:
            self._set_error("LlamaParse API key is required.")
            return
        if not gateway_url:
            self._set_error("Gateway URL is required.")
            return
        if not pdf_path:
            self._set_error("Please select a PDF file.")
            return

        self._save_settings()
        self._submit_btn.config(state="disabled")

        def _worker():
            try:
                self._set_progress("Reading PDF...")
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                self._set_progress("Calling LlamaParse... (this takes ~30-60s)")
                parsed = parse_pdf(pdf_bytes, api_key)

                self._set_progress("Submitting to gateway...")
                receipt_id = submit_parsed_paper(gateway_url, target_os, parsed)

                self.after(0, lambda: self._receipt_var.set(receipt_id))
                self.after(0, lambda: self._set_progress(
                    f"Done! Page count: {parsed.get('page_count', '?')}"))
            except ParseError as e:
                self.after(0, lambda: self._set_error(f"Parse rejected: {e}"))
                self.after(0, lambda: self._set_progress(""))
            except ParseUnavailable as e:
                self.after(0, lambda: self._set_error(f"LlamaParse unavailable: {e}"))
                self.after(0, lambda: self._set_progress(""))
            except GatewayError as e:
                self.after(0, lambda: self._set_error(f"Gateway error: {e}"))
                self.after(0, lambda: self._set_progress(""))
            except FileNotFoundError:
                self.after(0, lambda: self._set_error(f"File not found: {pdf_path}"))
                self.after(0, lambda: self._set_progress(""))
            except Exception as e:
                self.after(0, lambda: self._set_error(f"Unexpected error: {e}"))
                self.after(0, lambda: self._set_progress(""))
            finally:
                self.after(0, lambda: self._submit_btn.config(state="normal"))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_check_status(self):
        receipt_id = self._status_id_var.get().strip()
        gateway_url = self._url_var.get().strip() or self._cfg.get("gateway_url", "")

        if not receipt_id:
            messagebox.showwarning("Missing input", "Please enter a Receipt ID.")
            return

        self._status_text.config(state="normal")
        self._status_text.delete("1.0", "end")
        self._status_text.insert("end", "Fetching...")
        self._status_text.config(state="disabled")

        def _worker():
            try:
                data = check_status(gateway_url, receipt_id)
                pretty = json.dumps(data, indent=2)
            except GatewayError as e:
                pretty = f"Error: {e}"
            except Exception as e:
                pretty = f"Unexpected error: {e}"

            def _update():
                self._status_text.config(state="normal")
                self._status_text.delete("1.0", "end")
                self._status_text.insert("end", pretty)
                self._status_text.config(state="disabled")

            self.after(0, _update)

        threading.Thread(target=_worker, daemon=True).start()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()

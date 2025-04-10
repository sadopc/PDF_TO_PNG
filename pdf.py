import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import fitz  # PyMuPDF
import os
import threading
import sys

# --- Core Conversion Logic ---

def convert_pdf_to_png(pdf_path, status_callback, progress_callback, completion_callback):
    """
    Converts all pages of a PDF to PNG images.

    Args:
        pdf_path (str): Path to the input PDF file.
        status_callback (function): Function to update the status label text.
        progress_callback (function): Function to update progress (current_page, total_pages).
        completion_callback (function): Function to call when conversion is done or failed.
    """
    try:
        status_callback("Starting conversion...")
        
        # Validate input path
        if not pdf_path or not os.path.exists(pdf_path):
            raise ValueError("Invalid PDF file path.")
        if not pdf_path.lower().endswith(".pdf"):
             raise ValueError("Selected file is not a PDF.")

        # Determine output directory
        pdf_dir = os.path.dirname(pdf_path)
        pdf_filename = os.path.basename(pdf_path)
        pdf_name_without_ext = os.path.splitext(pdf_filename)[0]
        output_dir = os.path.join(pdf_dir, f"{pdf_name_without_ext}_pngs")

        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        status_callback(f"Outputting to: {output_dir}")

        # Open the PDF
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count

        if total_pages == 0:
             doc.close()
             raise ValueError("PDF file has no pages.")

        status_callback(f"Found {total_pages} page(s). Processing...")

        # Process each page
        for page_num in range(total_pages):
            page_index = page_num + 1
            progress_callback(page_index, total_pages)
            status_callback(f"Converting page {page_index}/{total_pages}...")

            page = doc.load_page(page_num)

            # Render page to an image (pixmap)
            # Increase zoom for higher resolution (e.g., zoom=2 means 144 dpi if base is 72)
            zoom = 2
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Define output PNG filename (with leading zeros for sorting)
            output_png_path = os.path.join(output_dir, f"page_{page_index:0{len(str(total_pages))}d}.png")

            # Save the pixmap as PNG
            pix.save(output_png_path)

            # Clean up pixmap object
            pix = None # dereference Pixmap

        # Clean up document object
        doc.close()
        status_callback(f"Success! {total_pages} pages converted to PNGs in:\n{output_dir}")

    except Exception as e:
        # Report errors
        error_message = f"Error: {e}"
        print(f"Conversion failed: {error_message}") # Log to console as well
        status_callback(error_message)
        completion_callback(success=False) # Signal failure
        return # Stop execution here on error

    # Signal success
    completion_callback(success=True)

# --- GUI Class ---

class PdfConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PDF to PNG Converter")
        # Make window slightly bigger
        self.root.geometry("550x300")
        # Make window non-resizable
        self.root.resizable(False, False)

        self.pdf_path = None
        self.is_converting = False

        # Style configuration
        self.style = ttk.Style(self.root)
        # Use a theme that might look more modern depending on the OS
        # 'clam', 'alt', 'default', 'classic' on many systems
        # 'vista' on windows, 'aqua' on macOS
        available_themes = self.style.theme_names()
        desired_themes = ['clam', 'alt', 'default'] # Fallback themes
        if sys.platform == "win32":
            desired_themes.insert(0,'vista')
        elif sys.platform == "darwin":
             desired_themes.insert(0,'aqua')

        for theme in desired_themes:
            if theme in available_themes:
                self.style.theme_use(theme)
                break

        self.style.configure("TButton", padding=6, relief="flat", font=('Helvetica', 10))
        self.style.configure("TLabel", padding=5, font=('Helvetica', 10))
        self.style.configure("Status.TLabel", font=('Helvetica', 9))
        self.style.configure("Header.TLabel", font=('Helvetica', 12, 'bold'))

        # --- Widgets ---
        # Header
        self.header_label = ttk.Label(root, text="Convert All PDF Pages to PNG", style="Header.TLabel")
        self.header_label.pack(pady=(10, 5))

        # Frame for file selection
        self.file_frame = ttk.Frame(root)
        self.file_frame.pack(fill=tk.X, padx=20, pady=5)

        self.select_button = ttk.Button(self.file_frame, text="Select PDF", command=self.select_pdf)
        self.select_button.pack(side=tk.LEFT, padx=(0, 10))

        self.file_label_var = tk.StringVar()
        self.file_label_var.set("No PDF selected")
        self.file_label = ttk.Label(self.file_frame, textvariable=self.file_label_var, wraplength=380, justify=tk.LEFT)
        self.file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Conversion button
        self.convert_button = ttk.Button(root, text="Convert to PNG", command=self.start_conversion_thread, state=tk.DISABLED)
        self.convert_button.pack(pady=10)

        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(root, orient="horizontal", length=400, mode="determinate", variable=self.progress_var)
        self.progress_bar.pack(pady=5)

        # Status label
        self.status_var = tk.StringVar()
        self.status_var.set("Please select a PDF file to begin.")
        self.status_label = ttk.Label(root, textvariable=self.status_var, style="Status.TLabel", wraplength=500, justify=tk.CENTER)
        self.status_label.pack(pady=(5, 10), fill=tk.X, expand=True)


    def select_pdf(self):
        if self.is_converting:
            return # Don't allow selection during conversion

        file_path = filedialog.askopenfilename(
            title="Select a PDF file",
            filetypes=[("PDF Files", "*.pdf")]
        )
        if file_path:
            self.pdf_path = file_path
            # Display potentially shortened path if too long
            display_path = self.pdf_path
            if len(display_path) > 60:
                display_path = "..." + display_path[-57:]
            self.file_label_var.set(display_path)
            self.convert_button.config(state=tk.NORMAL) # Enable convert button
            self.status_var.set("PDF selected. Ready to convert.")
            self.progress_var.set(0) # Reset progress
        else:
            # Keep previous state if selection was cancelled
            if not self.pdf_path:
                 self.file_label_var.set("No PDF selected")
                 self.convert_button.config(state=tk.DISABLED)
                 self.status_var.set("Please select a PDF file to begin.")


    def update_status(self, message):
        # Ensure GUI updates happen in the main thread
        self.root.after(0, lambda: self.status_var.set(message))

    def update_progress(self, current_page, total_pages):
         # Ensure GUI updates happen in the main thread
        progress = (current_page / total_pages) * 100
        self.root.after(0, lambda: self.progress_var.set(progress))

    def on_conversion_complete(self, success):
        # This function is called from the conversion thread via the callback
        # It schedules the final UI updates back on the main thread
        self.root.after(0, self._finalize_ui, success)

    def _finalize_ui(self, success):
        # This method runs in the main thread
        self.is_converting = False
        self.select_button.config(state=tk.NORMAL)
        self.convert_button.config(state=tk.NORMAL)
        if not success:
            # Optionally show an error dialog in addition to the status label
            messagebox.showerror("Conversion Failed", "An error occurred during conversion. Check status message for details.")
            self.progress_var.set(0) # Reset progress on failure
        # Status message is already set by convert_pdf_to_png


    def start_conversion_thread(self):
        if not self.pdf_path or self.is_converting:
            return

        self.is_converting = True
        self.select_button.config(state=tk.DISABLED)
        self.convert_button.config(state=tk.DISABLED)
        self.progress_var.set(0) # Reset progress bar
        self.status_var.set("Initializing...")

        # Run conversion in a separate thread to avoid freezing the GUI
        conversion_thread = threading.Thread(
            target=convert_pdf_to_png,
            args=(self.pdf_path, self.update_status, self.update_progress, self.on_conversion_complete),
            daemon=True # Allows the app to exit even if this thread is running
        )
        conversion_thread.start()

# --- Main Execution ---

if __name__ == "__main__":
    main_root = tk.Tk()
    app = PdfConverterApp(main_root)
    main_root.mainloop()
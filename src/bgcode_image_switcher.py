import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import tempfile
import qoi
import re
import numpy as np
from io import BytesIO

class QOIDecoder:
    def decode_from_bytes(self, qoi_bytes):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".qoi") as tmp:
            tmp.write(qoi_bytes)
            tmp.flush()
            try:
                image = qoi.read(tmp.name)
                if isinstance(image, np.ndarray):
                    return Image.fromarray(image)
                return image
            except Exception as e:
                print(f"Failed to decode QOI image: {e}")
                return None

class ImageExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Extractor")
        self.decoder = QOIDecoder()
        self.tk_images = []
        self.original_data = b''
        self.original_chunks = []
        self.replacement_chunks = []

        self.button_frame = tk.Frame(root)
        self.button_frame.pack(fill=tk.X, padx=10, pady=5)

        self.load_button = tk.Button(self.button_frame, text="Load .bgcode File", command=self.load_file)
        self.load_button.pack(side=tk.LEFT, padx=5)

        self.replace_button = tk.Button(self.button_frame, text="Replace with Another File", command=self.replace_file)
        self.replace_button.pack(side=tk.LEFT, padx=5)

        self.export_button = tk.Button(self.button_frame, text="Export Modified BGCode", command=self.export_file)
        self.export_button.pack(side=tk.LEFT, padx=5)

        self.tab_control = ttk.Notebook(root)
        self.tab_control.pack(expand=1, fill="both")

    def find_image_chunks(self, data):
        chunks = []
        qoi_marker = b'qoif'
        qoi_end_marker = b'\x00\x00\x00\x00\x00\x00\x00\x01'
        png_marker = b'\x89PNG\r\n\x1a\n'

        idx = 0
        while idx < len(data):
            if data[idx:idx+4] == qoi_marker:
                end = data.find(qoi_end_marker, idx)
                if end != -1:
                    end += len(qoi_end_marker)
                    chunks.append((idx, end, data[idx:end]))
                    idx = end
                else:
                    break
            elif data[idx:idx+8] == png_marker:
                end = data.find(b'IEND\xaeB`\x82', idx)
                if end != -1:
                    end += 8
                    chunks.append((idx, end, data[idx:end]))
                    idx = end
                else:
                    break
            else:
                idx += 1
        return chunks

    def load_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("BGCode Files", "*.bgcode")])
        if not filepath:
            return

        try:
            with open(filepath, 'rb') as f:
                self.original_data = f.read()
            self.original_chunks = self.find_image_chunks(self.original_data)
            self.display_images(self.original_chunks)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load file: {e}")

    def replace_file(self):
        filepath = filedialog.askopenfilename(filetypes=[("BGCode Files", "*.bgcode")])
        if not filepath:
            return

        try:
            with open(filepath, 'rb') as f:
                new_data = f.read()
            self.replacement_chunks = [chunk for (_, _, chunk) in self.find_image_chunks(new_data)]
            self.display_images([(0, 0, chunk) for chunk in self.replacement_chunks])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load replacement file: {e}")

    def export_file(self):
        if not self.replacement_chunks or len(self.replacement_chunks) != len(self.original_chunks):
            messagebox.showerror("Error", "Replacement file must contain the same number of images as the original.")
            return

        # Reconstruct data from scratch to avoid misalignment
        new_parts = []
        last_end = 0
        for (start, end, _), new_chunk in zip(self.original_chunks, self.replacement_chunks):
            new_parts.append(self.original_data[last_end:start])
            new_parts.append(new_chunk)
            last_end = end
        new_parts.append(self.original_data[last_end:])  # Append any remaining non-image data

        new_data = b''.join(new_parts)

        save_path = filedialog.asksaveasfilename(defaultextension=".bgcode", filetypes=[("BGCode Files", "*.bgcode")])
        if save_path:
            with open(save_path, 'wb') as f:
                f.write(new_data)
            messagebox.showinfo("Success", "Exported modified BGCode file successfully.")

    def display_images(self, chunk_entries):
        self.tk_images.clear()
        for tab in self.tab_control.tabs():
            self.tab_control.forget(tab)

        image_count = 0
        for (_, _, chunk) in chunk_entries:
            image = None
            if chunk.startswith(b'qoif'):
                image = self.decoder.decode_from_bytes(chunk)
            elif chunk.startswith(b'\x89PNG\r\n\x1a\n'):
                try:
                    image = Image.open(BytesIO(chunk))
                except Exception as e:
                    print(f"Error decoding PNG image: {e}")

            if isinstance(image, Image.Image):
                frame = ttk.Frame(self.tab_control)
                canvas = tk.Canvas(frame, width=image.width, height=image.height)
                canvas.pack(expand=True, fill='both')
                tk_img = ImageTk.PhotoImage(image)
                self.tk_images.append(tk_img)
                canvas.create_image(0, 0, anchor='nw', image=tk_img)
                self.tab_control.add(frame, text=f"Image {image_count + 1}")
                image_count += 1

if __name__ == '__main__':
    root = tk.Tk()
    app = ImageExtractorApp(root)
    root.mainloop()
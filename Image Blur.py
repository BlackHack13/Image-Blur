import os
import customtkinter as ctk
from PIL import Image, ImageTk, ImageFilter, ExifTags
import time

# Die Klasse ist verantwortlich für die Bildlogik wie das Laden, Anwenden von Unschärfefiltern und Rotationen
class ImageProcessor:
    def __init__(self, image_folder):
        # Initialisiere die Ordnerpfade, Unschärfestufen und Rotationsparameter
        self.image_folder = image_folder
        self.image_files = [os.path.join(image_folder, file) for file in os.listdir(image_folder) if file.lower().endswith(('png', 'jpg', 'jpeg'))]
        self.start_blur_level = 24
        self.max_blur_level = 24
        self.min_blur_level = 0
        self.step_size = 4
        self.manual_rotation = 0
        self.current_image_index = 0
        self.blur_type = "gaussian"  # Standardmäßig wird der Gaussian-Blur verwendet

    # Gibt den Pfad des aktuellen Bildes zurück
    def get_current_image_path(self):
        return self.image_files[self.current_image_index]

    # Lädt das nächste Bild und setzt Unschärfe und Rotation zurück
    def next_image(self):
        self.current_image_index = (self.current_image_index + 1) % len(self.image_files)
        self.start_blur_level = self.max_blur_level  # Zurück zur maximalen Unschärfe
        self.manual_rotation = 0  # Manuelle Drehung zurücksetzen

    # Wendet den ausgewählten Unschärfefilter auf das Bild an
    def apply_blur_effect(self, image):
        if self.blur_type == "gaussian":
            return image.filter(ImageFilter.GaussianBlur(self.start_blur_level))
        elif self.blur_type == "box":
            return image.filter(ImageFilter.BoxBlur(self.start_blur_level))
        elif self.blur_type == "min":
            return image.filter(ImageFilter.MinFilter(size=self.start_blur_level * 2 + 1))
        elif self.blur_type == "max":
            return image.filter(ImageFilter.MaxFilter(size=self.start_blur_level * 2 + 1))
        else:
            return image.filter(ImageFilter.GaussianBlur(self.start_blur_level))

    # Lädt das Bild, wendet die Unschärfe und die Rotation an und passt die Größe an
    def load_image_with_blur(self, canvas_width, canvas_height):
        image_path = self.get_current_image_path()
        image = Image.open(image_path)

        # EXIF-Daten verwenden, um die richtige Bildorientierung zu gewährleisten
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = image._getexif()

            if exif is not None:
                orientation_value = exif.get(orientation, None)
                if orientation_value == 3:
                    image = image.rotate(180, expand=True)
                elif orientation_value == 6:
                    image = image.rotate(270, expand=True)
                elif orientation_value == 8:
                    image = image.rotate(90, expand=True)
        except (AttributeError, KeyError, IndexError):
            pass

        # Anwenden der manuellen Drehung
        image = image.rotate(self.manual_rotation, expand=True)

        # Bildgröße an das Canvas anpassen
        image = image.resize((canvas_width, canvas_height), Image.LANCZOS)

        # Wendet die entsprechende Unschärfe auf das Bild an
        return self.apply_blur_effect(image)

    # Erhöht die Unschärfestufe um den Schrittwert
    def make_blurrier(self):
        if self.start_blur_level < self.max_blur_level:
            self.start_blur_level = min(self.max_blur_level, self.start_blur_level + self.step_size)

    # Reduziert die Unschärfestufe um den Schrittwert
    def make_sharper(self):
        if self.start_blur_level > self.min_blur_level:
            self.start_blur_level = max(self.min_blur_level, self.start_blur_level - self.step_size)

    # Bild um 90° nach links drehen
    def rotate_left(self):
        self.manual_rotation = (self.manual_rotation - 90) % 360

    # Bild um 90° nach rechts drehen
    def rotate_right(self):
        self.manual_rotation = (self.manual_rotation + 90) % 360

    # Ändert den Unschärfefilter
    def change_blur_type(self, new_blur_type):
        self.blur_type = new_blur_type


# Die Klasse 'GUI' ist verantwortlich für das Benutzerinterface und die Interaktion des Benutzers
class GUI:
    def __init__(self, root, image_processor):
        self.root = root
        self.image_processor = image_processor
        self.start_time = 0
        self.canvas_width = 600
        self.canvas_height = 600

        # Layout der GUI festlegen
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0)

        # Timer Label erstellen (oben rechts)
        self.timer_label = ctk.CTkLabel(root, text="Zeit: 00:00", font=("Arial", 25), fg_color="white", text_color="black", corner_radius=15)
        self.timer_label.grid(row=0, column=1, sticky="ne", padx=20, pady=20)

        # Canvas für Bildanzeige (mittig)
        self.canvas = ctk.CTkCanvas(root, width=self.canvas_width, height=self.canvas_height)
        self.canvas.grid(row=0, column=0, padx=20, pady=20)

        # Widgets für Steuerung unter dem Bild (Schärfer, Unschärfer, Nächstes Bild)
        self.create_widgets()

        # Rechts vom Bild: Unschärfeauswahl und Drehen (Platz unter dem Timer)
        self.create_side_widgets()

        # Zeigt das erste Bild an
        self.display_image()
        self.start_timer()

    # Erstellt die Buttons unter dem Bild
    def create_widgets(self):
        button_blurrier = ctk.CTkButton(self.root, text="⇩ Unschärfer", corner_radius=10, command=self.make_blurrier)
        button_blurrier.grid(row=1, column=0, sticky="w", padx=20, pady=10)

        button_sharper = ctk.CTkButton(self.root, text="⇧ Schärfer", corner_radius=10, command=self.make_sharper)
        button_sharper.grid(row=1, column=0, padx=20, pady=10)

        button_next = ctk.CTkButton(self.root, text="➡ Nächstes Bild", corner_radius=10, command=self.next_image)
        button_next.grid(row=1, column=0, sticky="e", padx=20, pady=10)

    # Erstellt die Widgets rechts vom Bild (Blurauswahl, Drehen)
    def create_side_widgets(self):
        # Dropdown-Menü zur Auswahl des Unschärfefilters unter dem Timer
        blur_options = ["gaussian", "box", "min", "max"]
        self.blur_type_menu = ctk.CTkComboBox(self.root, values=blur_options, corner_radius=5, command=self.change_blur_type)
        self.blur_type_menu.set(blur_options[0])  # Standardmäßig "gaussian"
        self.blur_type_menu.configure(state="readonly")
        self.blur_type_menu.grid(row=0, column=1, padx=20, pady=(60, 10), sticky="n")  # Unter dem Timer

        # Drehen Buttons unter der Unschärfeauswahl
        button_rotate_left = ctk.CTkButton(self.root, text="↺ Links drehen", corner_radius=10, command=self.rotate_left)
        button_rotate_left.grid(row=0, column=1, padx=20, pady=(100, 10))

        button_rotate_right = ctk.CTkButton(self.root, text="↻ Rechts drehen", corner_radius=10, command=self.rotate_right)
        button_rotate_right.grid(row=0, column=1, padx=20, pady=10)

    # Zeigt das aktuelle Bild im Canvas an
    def display_image(self):
        image = self.image_processor.load_image_with_blur(self.canvas_width, self.canvas_height)
        img = ImageTk.PhotoImage(image)
        self.canvas.create_image(0, 0, anchor="nw", image=img)
        self.canvas.image = img  # Referenz speichern, um Garbage Collection zu verhindern

    # Wechsel zum nächsten Bild
    def next_image(self):
        self.image_processor.next_image()
        self.display_image()
        self.start_timer()

    # Macht das Bild unschärfer
    def make_blurrier(self):
        self.image_processor.make_blurrier()
        self.display_image()

    # Macht das Bild schärfer
    def make_sharper(self):
        self.image_processor.make_sharper()
        self.display_image()

    # Bild um 90° nach links drehen
    def rotate_left(self):
        self.image_processor.rotate_left()
        self.display_image()

    # Bild um 90° nach rechts drehen
    def rotate_right(self):
        self.image_processor.rotate_right()
        self.display_image()

    # Ändert den Unschärfefilter
    def change_blur_type(self, new_blur_type):
        self.image_processor.change_blur_type(new_blur_type)
        self.display_image()

    # Startet den Timer für das aktuelle Bild
    def start_timer(self):
        self.start_time = time.time()
        self.update_timer()

    # Aktualisiert die Timer-Anzeige
    def update_timer(self):
        elapsed_time = int(time.time() - self.start_time)
        minutes = elapsed_time // 60
        seconds = elapsed_time % 60
        self.timer_label.configure(text=f"Zeit: {minutes:02}:{seconds:02}")
        self.root.after(1000, self.update_timer)


# Startet Hauptprogramm
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")  # Setzt den Modus auf "dark" für dunkles Theme
    ctk.set_default_color_theme("blue")  # Setzt das Farbschema
    root = ctk.CTk()
    root.title("Bilderraten")
    image_folder = "Bilder"
    image_processor = ImageProcessor(image_folder)
    app = GUI(root, image_processor)
    root.mainloop()

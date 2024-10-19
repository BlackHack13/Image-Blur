import os
import random
import customtkinter as ctk  # Bibliothek für eine benutzerdefinierte grafische Oberfläche
from PIL import Image, ImageTk, ImageFilter, ExifTags, ImageOps  # Bibliothek für Bildverarbeitung
import time  # Zum Messen der Zeit

BLUR_METHODS = ["gaussian", "box", "min", "max", "grayscale", "solarize", "posterize", "invert"]
# Klasse zur Bildverarbeitung
class ImageProcessor:
    def __init__(self, image_folder):
        self.image_folder = image_folder
        self.image_files = [os.path.join(image_folder, file) for file in os.listdir(image_folder) if file.lower().endswith(('png', 'jpg', 'jpeg'))]
        self.start_blur_level = 0  # Startwert für die Unschärfe, standardmäßig kein Blur
        self.max_blur_level = 24  # Maximale Unschärfe
        self.min_blur_level = 0  # Minimale Unschärfe
        self.step_size = 4  # Schrittgröße zur Änderung der Unschärfe
        self.manual_rotation = 0  # Bildrotation (manuell)
        self.current_image_index = 0  # Aktuell angezeigtes Bild
        self.blur_type = None  # Blur muss manuell ausgewählt werden
        self.split_enabled = True  # Standardmäßig ist das Bild in Rechtecke aufgeteilt
        self.grid_size = 4  # Anzahl der Start Rechtecke
        self.original_image = None  # Speichert das unveränderte Originalbild
        self.shuffled_pieces = None  # Speichert die gemischten Teile des Bildes
        self.rotation_angles = []  # Liste der Drehwinkel für jedes Teil

    # Gibt den Pfad des aktuell ausgewählten Bildes zurück
    def get_current_image_path(self):
        return self.image_files[self.current_image_index]

    # Wechselt zum nächsten Bild in der Liste
    def next_image(self):
        self.current_image_index = (self.current_image_index + 1) % len(self.image_files)
        self.reset_image_state()

    # Setzt den Zustand des Bildes zurück (Unschärfe, Rotation, etc.)
    def reset_image_state(self):
        self.start_blur_level = self.min_blur_level  # Blur wird auf Minimum gesetzt
        self.manual_rotation = 0
        self.original_image = None
        self.shuffled_pieces = None
        self.rotation_angles = []  # Zurücksetzen der Rotationen für Teile

    # Wendet einen Unschärfe-Filter auf das Bild an, wenn ein Blur-Typ ausgewählt ist
    def apply_blur_effect(self, image):
        if self.blur_type:
            blur_methods = {
                "gaussian": ImageFilter.GaussianBlur(radius=self.start_blur_level),
                "box": ImageFilter.BoxBlur(radius=self.start_blur_level),
                "min": ImageFilter.MinFilter(size=self.start_blur_level * 2 + 1),
                "max": ImageFilter.MaxFilter(size=self.start_blur_level * 2 + 1)
            }

            selected_filter = blur_methods.get(self.blur_type)
            if selected_filter:
                return image.filter(selected_filter)
            elif self.blur_type == "grayscale":
                return ImageOps.grayscale(image)
            elif self.blur_type == "solarize":
                return ImageOps.solarize(image, threshold=128)
            elif self.blur_type == "posterize":
                return ImageOps.posterize(image, bits=2)
            elif self.blur_type == "invert":
                return ImageOps.invert(image)

        return image  # Return the image unchanged if no blur type is selected

    # Lädt das Originalbild und passt es in die gegebene Canvas-Größe an
    def load_original_image(self, canvas_width, canvas_height):
        image_path = self.get_current_image_path()

        if self.original_image is None:
            image = Image.open(image_path)

            # Exif-Daten auslesen, um die Bildorientierung zu korrigieren
            try:
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == 'Orientation':
                        break
                exif = image._getexif()

                # Überprüft die Orientierung und dreht das Bild falls nötig
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

            # Bild manuell rotieren, wenn der Benutzer es festgelegt hat
            image = image.rotate(self.manual_rotation, expand=True)
            # Bild auf die gewünschte Größe skalieren
            image = image.resize((canvas_width, canvas_height), Image.LANCZOS)
            self.original_image = image  # Speichert das Originalbild
        return self.original_image.copy()  # Gibt eine Kopie des Originalbildes zurück

    # Lädt das Bild mit dem angewendeten Unschärfe-Effekt
    def load_image_with_blur(self, canvas_width, canvas_height):
        image = self.load_original_image(canvas_width, canvas_height)

        # Falls die Bildaufteilung aktiviert ist
        if self.split_enabled:
            if self.shuffled_pieces is None:
                # Zerteilt und mischt das Bild, wenn es noch nicht getan wurde
                self.shuffled_pieces = self.split_and_shuffle_image(image, self.grid_size)
            # Setzt das Bild aus den unscharfen oder scharfen Teilen neu zusammen
            return self.reconstruct_image_from_pieces(self.shuffled_pieces, (canvas_width, canvas_height))

        # Wenn keine Rechtecke aktiviert sind, wende den Unschärfe-Effekt auf das gesamte Bild an
        return self.apply_blur_effect(image)

    # Teilt das Bild in Rechtecke und mischt sie
    def split_and_shuffle_image(self, image, grid_size):
        width, height = image.size
        piece_width = width // grid_size
        piece_height = height // grid_size

        pieces = []
        self.rotation_angles = []  # Initialisiere eine Liste, um die Rotationen der Teile zu speichern
        for i in range(grid_size):
            for j in range(grid_size):
                left = j * piece_width
                top = i * piece_height
                right = (j + 1) * piece_width
                bottom = (i + 1) * piece_height
                piece = image.crop((left, top, right, bottom))  # Ein Rechteck vom Bild ausschneiden
                pieces.append(piece)
                self.rotation_angles.append(0)

        random.shuffle(pieces)  # Die Teile zufällig mischen
        return pieces, piece_width, piece_height

    # Setzt das Bild aus den gemischten Teilen wieder zusammen und wendet dynamisch den Unschärfe-Effekt an
    def reconstruct_image_from_pieces(self, pieces_info, image_size):
        pieces, piece_width, piece_height = pieces_info
        new_image = Image.new('RGB', image_size)
        idx = 0
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                piece = pieces[idx].copy()  # Ein Bildteil kopieren
                # Wendet den Unschärfe-Effekt auf das Teil an, wenn ein Blur-Typ ausgewählt ist
                piece = self.apply_blur_effect(piece)
                # Dreht das Bildteil, wenn eine manuelle Drehung angewendet wurde
                piece = piece.rotate(self.rotation_angles[idx], expand=True)
                new_image.paste(piece, (j * piece_width, i * piece_height))  # Das Teil auf das neue Bild positionieren
                idx += 1
        return new_image

    # Ändert den Unschärfegrad
    def change_blur_level(self, direction):
        if direction == "increase":
            self.start_blur_level = min(self.start_blur_level + self.step_size, self.max_blur_level)
        elif direction == "decrease":
            self.start_blur_level = max(self.start_blur_level - self.step_size, self.min_blur_level)
        self.original_image = None

    # Ändert den Unschärfetyp
    def change_blur_type(self, new_blur_type):
        if new_blur_type is None:
            # Keine Unschärfe anwenden (Kein Blur)
            self.blur_type = None
        elif new_blur_type in BLUR_METHODS:
            # Setze den Blur-Typ und den maximalen Blur-Level, wenn vorher kein Blur-Typ aktiv war
            if self.blur_type is None:  # Wenn kein Blur ausgewählt war
                self.start_blur_level = self.max_blur_level  # Setzt den maximalen Blur-Level
            self.blur_type = new_blur_type
        else:
            raise ValueError(f"Unbekannter Blur-Typ: {new_blur_type}")
        self.original_image = None  # Bild muss neu geladen werden

    # Dreht das Bild nach links oder rechts
    def rotate_image(self, direction):
        angle = -90 if direction == "left" else 90
        if self.split_enabled:
            # Drehe jedes Teil des Bildes individuell
            self.rotation_angles = [(rot_angle + angle) % 360 for rot_angle in self.rotation_angles]
        else:
            # Dreht das gesamte Bild
            self.manual_rotation = (self.manual_rotation + angle) % 360
        self.original_image = None

    # Aktiviert oder deaktiviert die Bildaufteilung
    def toggle_split(self, state):
        self.split_enabled = state
        self.shuffled_pieces = None
        self.rotation_angles = []  # Zurücksetzen der Rotationen für Teile

    # Ändert die Größe des Gitters, das das Bild zerteilt
    def adjust_grid_size(self, direction):
        if direction == "increase":
            self.grid_size = min(self.grid_size + 1, 10)
        elif direction == "decrease":
            self.grid_size = max(self.grid_size - 1, 2)
        self.shuffled_pieces = None  # Setzt gemischte Bildteile zurück
        self.rotation_angles = []  # Zurücksetzen der Rotationen für Teile

    # Gibt das aktuell verarbeitete Bild zurück
    def get_processed_image_with_effects(self, canvas_width, canvas_height):
        return self.load_image_with_blur(canvas_width, canvas_height)

# Klasse zur grafischen Benutzeroberfläche (GUI)
class GUI:
    def __init__(self, root, image_processor):
        self.root = root
        self.image_processor = image_processor
        self.current_image = None
        self.start_time = 0  # Startzeit des Timers
        self.canvas_width = 600  # Breite des Bildbereichs (Canvas)
        self.canvas_height = 600  # Höhe des Bildbereichs (Canvas)

        # Layout-Konfiguration für das Hauptfenster (Grid-Struktur)
        self.root.grid_columnconfigure(0, weight=1)  # Bildbereich (Canvas)
        self.root.grid_columnconfigure(1, weight=0)  # Rechte Seitenleiste
        self.root.grid_rowconfigure(0, weight=0)  # Button Bereich (oben)
        self.root.grid_rowconfigure(1, weight=1)  # Hauptbereich (für das Bild)
        self.root.grid_rowconfigure(2, weight=0)  # Bereich für die Buttons unten

        # Canvas-Bereich für das Bild (unter dem Button)
        self.canvas = ctk.CTkCanvas(self.root, width=self.canvas_width, height=self.canvas_height)
        self.canvas.grid(row=1, column=0, padx=20, pady=20)  # Platzierung in der Zeile unter dem Button

        # Erstellt die Buttons und Widgets für die Interaktionen
        self.create_widgets()

        # Zeigt das erste Bild an und startet den Timer
        self.display_image()
        self.start_timer()

        # Erstellt die Haupt-Buttons unter dem Bild (Unschärfer, Schärfer, Nächstes Bild)

    def create_widgets(self):
        # Button zum Speichern des Bildes (oben, über dem Bild)
        self.save_button = ctk.CTkButton(self.root, text="Bild Speichern", command=self.open_save_dialog)
        self.save_button.grid(row=0, column=0, padx=10, pady=10, sticky="nw")  # Platzierung in der obersten Zeile

        # Buttons unter dem Bild
        button_frame = ctk.CTkFrame(self.root)  # Rahmen für die Buttons
        button_frame.grid(row=2, column=0, pady=10)

        # Button, um die Anzahl der Rechtecke zu erhöhen
        button_increase_grid = ctk.CTkButton(button_frame, text="⬆️ Mehr Rechtecke", corner_radius=10, command=lambda: self.adjust_grid_size("increase"))
        button_increase_grid.grid(row=0, column=0, padx=5, pady=5)  # Direkt unter den Unschärfer-Button

        # Button, um die Anzahl der Rechtecke zu verringern
        button_decrease_grid = ctk.CTkButton(button_frame, text="⬇️ Weniger Rechtecke", corner_radius=10,command=lambda: self.adjust_grid_size("decrease"))
        button_decrease_grid.grid(row=0, column=1, padx=5, pady=5)  # Direkt unter den Schärfer-Button

        # Button, um das Bild unschärfer zu machen
        self.button_blurrier = ctk.CTkButton(button_frame, text="⇩ Unschärfer", corner_radius=10, command=lambda: self.change_blur_level("increase"), state="disabled")
        self.button_blurrier.grid(row=1, column=0, padx=5, pady=5)  # Platzierung im Button-Rahmen

        # Button, um das Bild schärfer zu machen
        self.button_sharper = ctk.CTkButton(button_frame, text="⇧ Schärfer", corner_radius=10, command=lambda: self.change_blur_level("decrease"), state="disabled")
        self.button_sharper.grid(row=1, column=1, padx=5, pady=5)  # Platzierung im Button-Rahmen

        # Button, um zum nächsten Bild zu wechseln, rechts neben den anderen Buttons
        button_next = ctk.CTkButton(button_frame, text="➡ Nächstes Bild", corner_radius=10, command=self.next_image)
        button_next.grid(row=0, column=2, rowspan=2, padx=10, pady=5)  # Platzierung rechts neben den 4 Buttons (2 Zeilen hoch)

        # Widgets an der rechten Seite (z.B. für Rotation und Bildzerlegung)
        side_frame = ctk.CTkFrame(self.root)
        side_frame.grid(row=1, column=1, padx=20, pady=(self.canvas_height // 4), sticky="n")  # Mittige Höhe relativ zur Bildgröße

        # Dropdown-Menü, um den Unschärfetyp auszuwählen
        blur_options = ["Kein Blur"] + BLUR_METHODS
        self.blur_type_menu = ctk.CTkComboBox(side_frame, values=blur_options, corner_radius=5, command=self.on_blur_type_selected)
        self.blur_type_menu.set("Blureffekt:")  # Platzhalter für das Dropdown-Menü
        self.blur_type_menu.configure(state="readonly")
        self.blur_type_menu.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        # Button, um das Bild nach links zu drehen
        button_rotate_left = ctk.CTkButton(side_frame, text="↺ Links drehen", corner_radius=10, command=lambda: self.rotate_image("left"))
        button_rotate_left.grid(row=1, column=0, padx=5, pady=5, sticky="w")

        # Button, um das Bild nach rechts zu drehen
        button_rotate_right = ctk.CTkButton(side_frame, text="↻ Rechts drehen", corner_radius=10, command=lambda: self.rotate_image("right"))
        button_rotate_right.grid(row=2, column=0, padx=5, pady=5, sticky="w")

        # Checkbox, um das Bild in Rechtecke zu teilen, standardmäßig aktiviert
        self.split_check = ctk.CTkCheckBox(side_frame, text="Bild zerteilen", command=self.toggle_split)
        self.split_check.select()  # Standardmäßig aktiviert
        self.split_check.grid(row=3, column=0, padx=5, pady=5, sticky="w")

        # Timer oben rechts im Fenster platzieren
        self.timer_label = ctk.CTkLabel(self.root, text="Zeit: 00:00", font=("Arial", 25), fg_color="white", text_color="black", corner_radius=15)
        self.timer_label.grid(row=0, column=1, sticky="ne", padx=20, pady=20)

    # Wird aufgerufen, wenn ein Unschärfetyp im Dropdown ausgewählt wird
    def on_blur_type_selected(self, selected_blur_type):
        if selected_blur_type == "Kein Blur":
            # Deaktiviert die Schärfer-/Unschärfer-Buttons
            self.button_blurrier.configure(state="disabled")
            self.button_sharper.configure(state="disabled")
            # Entfernt den Blur-Effekt
            self.image_processor.change_blur_type(None)  # Keine Unschärfe
        elif selected_blur_type in BLUR_METHODS:
            # Aktiviert die Schärfer-/Unschärfer-Buttons
            self.button_blurrier.configure(state="normal")
            self.button_sharper.configure(state="normal")
            # Setzt den ausgewählten Blur-Typ und wendet ihn auf das Bild an
            self.image_processor.change_blur_type(selected_blur_type)

        # Aktualisiert die Anzeige des Bildes
        self.display_image()

    # Zeigt das aktuelle Bild auf der Leinwand (Canvas) an
    def display_image(self):
        image = self.image_processor.load_image_with_blur(self.canvas_width, self.canvas_height)  # Bild mit Unschärfe laden
        img = ImageTk.PhotoImage(image)  # In ein format umwandeln, das tkinter anzeigen kann
        self.canvas.create_image(0, 0, anchor="nw", image=img)  # Bild auf dem Canvas platzieren
        self.canvas.image = img  # Das Bild speichern, damit es nicht vom Garbage Collector entfernt wird

    # Wechselt zum nächsten Bild und zeigt es an
    def next_image(self):
        self.image_processor.next_image()  # Bild wechseln
        self.display_image()  # Neues Bild anzeigen
        self.start_timer()  # Timer für das neue Bild zurücksetzen und starten

    # Ändert den Unschärfegrad und zeigt das Bild neu an
    def change_blur_level(self, direction):
        self.image_processor.change_blur_level(direction)  # Unschärfe erhöhen/verringern
        self.display_image()  # Bild mit neuem Unschärfegrad anzeigen

    # Dreht das Bild nach links oder rechts und zeigt es neu an
    def rotate_image(self, direction):
        self.image_processor.rotate_image(direction)  # Bild rotieren
        self.display_image()  # Bild mit neuer Rotation anzeigen

    # Ändert den Unschärfetyp und zeigt das Bild neu an
    def change_blur_type(self, new_blur_type):
        self.image_processor.change_blur_type(new_blur_type)  # Unschärfetyp ändern
        self.display_image()  # Bild mit neuem Unschärfetyp anzeigen

    # Aktiviert oder deaktiviert das Zerteilen des Bildes
    def toggle_split(self):
        self.image_processor.toggle_split(self.split_check.get())  # Bild zerteilen/zusammenfügen
        self.display_image()  # Neues Bild anzeigen

    # Ändert die Anzahl der Bildteile (Grid-Größe) und zeigt das Bild neu an
    def adjust_grid_size(self, direction):
        self.image_processor.adjust_grid_size(direction)  # Grid-Größe ändern
        self.display_image()  # Bild mit neuer Grid-Größe anzeigen

    # Startet den Timer für die Anzeige eines Bildes
    def start_timer(self):
        self.start_time = time.time()  # Aktuelle Zeit als Startzeit speichern
        self.update_timer()  # Timer-Label aktualisieren

    # Aktualisiert den Timer jede Sekunde
    def update_timer(self):
        elapsed_time = int(time.time() - self.start_time)  # Verstrichene Zeit berechnen
        minutes = elapsed_time // 60  # Minuten berechnen
        seconds = elapsed_time % 60  # Sekunden berechnen
        self.timer_label.configure(text=f"Zeit: {minutes:02}:{seconds:02}")  # Timer-Label aktualisieren
        self.root.after(1000, self.update_timer)  # Diese Methode alle 1000 ms (1 Sekunde) erneut aufrufen

    # Funktion zum Öffnen des Dialogs zur Auswahl des Speicherformats
    def open_save_dialog(self):
        save_dialog = ctk.CTkToplevel(self.root)  # Neues CTK Fenster öffnen
        save_dialog.title("Speicherformat auswählen")

        # Label zur Anzeige der Anweisung
        label = ctk.CTkLabel(save_dialog, text="Wähle das Speicherformat:", font=("Arial", 12))
        label.pack(padx=20, pady=10)

        # Button zum Speichern im JPG-Format
        jpg_button = ctk.CTkButton(save_dialog, text="Als JPG speichern", command=lambda: self.save_image_with_format('jpg', save_dialog))
        jpg_button.pack(pady=5)

        # Button zum Speichern im PDF-Format
        pdf_button = ctk.CTkButton(save_dialog, text="Als PDF speichern", command=lambda: self.save_image_with_format('pdf', save_dialog))
        pdf_button.pack(pady=5)

    # Funktion zum Speichern des Bildes im ausgewählten Format
    def save_image_with_format(self, format_type, dialog):
        processed_image = self.image_processor.get_processed_image_with_effects(self.canvas_width, self.canvas_height)
        file_extension = format_type.lower()  # 'jpg' oder 'pdf'
        file_name = f"saved_image.{file_extension}"

        # Speichere das Bild im gewählten Format
        if format_type == 'jpg':
            processed_image.save(file_name, "JPEG")
        elif format_type == 'pdf':
            processed_image.save(file_name, "PDF")

        dialog.destroy()  # Schließt den Dialog


# Der Hauptteil des Programms, der das Fenster und die GUI startet
if __name__ == "__main__":
    ctk.set_appearance_mode("dark")  # Setzt den Dark Mode für die GUI
    ctk.set_default_color_theme("blue")  # Setzt das blaue Farbschema
    root = ctk.CTk()
    root.title("Bilderraten")
    image_folder = "Bilder"  # Der Ordner, in dem sich die Bilder befinden
    image_processor = ImageProcessor(image_folder)
    app = GUI(root, image_processor)
    root.mainloop()  # Startet die Hauptschleife der GUI

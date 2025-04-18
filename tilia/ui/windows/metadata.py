import functools

from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFrame,
    QVBoxLayout,
    QWidget,
    QDialogButtonBox,
)

from tilia.settings import settings
from tilia.requests import get, Get, post, Post, listen
from tilia.ui.windows import WindowKind
from tilia.ui.format import format_media_time
from tilia.ui.windows.metadata_edit_notes import EditNotesDialog
from tilia.ui.windows.metadata_edit_fields import EditMetadataFieldsDialog
import tilia.errors


class MediaMetadataWindow(QDialog):
    KIND = WindowKind.MEDIA_METADATA

    SEPARATE_WINDOW_FIELDS = ["notes"]
    READ_ONLY_FIELDS = {
        "media length": functools.partial(get, Get.MEDIA_DURATION),
        "media path": functools.partial(get, Get.MEDIA_PATH),
    }

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Metadata")
        self.metadata = {}
        self.metadata_original = {}
        self.fields_to_formatters = {"media length": format_media_time}
        self.setMinimumSize(settings.get("media_metadata", "window_width"), 0)
        listen(
            self,
            Post.SETTINGS_UPDATED,
            self.on_settings_updated,
        )
        self.setLayout(QVBoxLayout())
        self.setup_layout()
        self.show()

        post(Post.WINDOW_OPEN_DONE, WindowKind.MEDIA_METADATA)

    def setup_layout(self):
        self._setup_widgets()
        self._setup_window_buttons()
        self._setup_fields()

    def _setup_fields(self):
        self.populate_with_editable_fields()
        self.add_separator()
        self.populate_with_read_only_fields()
        self.setup_buttons()
        self.adjustSize()

    def _setup_widgets(self):
        self.form_layout = QFormLayout()
        content = QWidget()
        content.setLayout(self.form_layout)
        self.layout().addWidget(content)

    def _setup_window_buttons(self):
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(
            self.apply_fields
        )
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(
            self.close
        )
        self.layout().addWidget(self.button_box)

    def add_separator(self):
        line = QFrame()
        line.setFrameStyle(QFrame.Shape.HLine | QFrame.Shadow.Sunken)
        self.form_layout.addRow(line)

    def clear_layout(self):
        while self.form_layout.rowCount():
            self.form_layout.removeRow(0)

    def populate_with_editable_fields(self):
        metadata = get(Get.MEDIA_METADATA)
        self.metadata.clear()
        self.metadata_original.clear()
        for name, value in metadata.items():
            if name in list(self.READ_ONLY_FIELDS) + self.SEPARATE_WINDOW_FIELDS:
                continue
            line_edit = QLineEdit(str(value))
            self.form_layout.addRow(QLabel(name.capitalize()), line_edit)
            self.metadata[name] = line_edit
            self.metadata_original[name] = value

    def populate_with_read_only_fields(self):
        for name, getter in self.READ_ONLY_FIELDS.items():
            value = getter()
            if name in self.fields_to_formatters:
                value = self.fields_to_formatters[name](value)
            value_label = QLabel(value)
            value_label.setWordWrap(True)
            self.form_layout.addRow(QLabel(name.capitalize()), value_label)

    def setup_buttons(self):
        edit_notes_button = QPushButton("Edit notes...")
        edit_notes_button.clicked.connect(self.on_edit_notes_button)
        self.form_layout.addRow(edit_notes_button)

        edit_fields_button = QPushButton("Edit fields...")
        edit_fields_button.clicked.connect(self.on_edit_metadata_fields_button)
        self.form_layout.addRow(edit_fields_button)

    def on_edit_notes_button(self):
        dialog = EditNotesDialog()
        accepted = dialog.exec()
        if accepted:
            post(Post.MEDIA_METADATA_FIELD_SET, "notes", dialog.get_result())

    def on_edit_metadata_fields_button(self):
        edited_fields = self._get_edits()
        if edited_fields and not get(
            Get.FROM_USER_YES_OR_NO,
            "Save metadata edits",
            "Leave window without saving changes?",
        ):
            return
        self._save_edits(edited_fields)
        dialog = EditMetadataFieldsDialog()
        accepted = dialog.exec()
        if accepted:
            valid_fields, invalid_fields = dialog.get_result()
            if invalid_fields:
                self.display_invalid_field_error(invalid_fields)

            self.update_metadata_fields(valid_fields)
            self.refresh_fields()

    @staticmethod
    def display_invalid_field_error(invalid_fields: list[str]):
        tilia.errors.display(
            tilia.errors.METADATA_FIELD_INVALID, "\n".join(invalid_fields)
        )

    def refresh_fields(self) -> None:
        self.clear_layout()
        self._setup_fields()

    def focus(self):
        pass  # TODO: set focus on self

    def closeEvent(self, event):
        edited_fields = self._get_edits()
        if edited_fields and not get(
            Get.FROM_USER_YES_OR_NO,
            "Save metadata edits",
            "Close window without saving changes?",
        ):
            event.ignore()
            return
        post(Post.WINDOW_CLOSE_DONE, WindowKind.MEDIA_METADATA)
        super().closeEvent(event)

    def update_metadata_fields(self, new_fields: list[str]):
        fields_without_required = [
            item
            for item in self.metadata.keys()
            if item not in get(Get.MEDIA_METADATA_REQUIRED_FIELDS)
        ]

        if not fields_without_required == new_fields:
            post(
                Post.METADATA_UPDATE_FIELDS,
                get(Get.MEDIA_METADATA_REQUIRED_FIELDS) + new_fields,
            )

    def apply_fields(self):
        self._save_edits(self._get_edits())
        self.clear_layout()
        self._setup_fields()

    def _get_edits(self) -> dict:
        return {
            name: self.metadata[name].text()
            for name in self.metadata
            if name in self.metadata_original
            and self.metadata[name].text() != self.metadata_original[name]
        }

    def _save_edits(self, edited_fields: dict) -> None:
        for name, value in edited_fields.items():
            post(Post.MEDIA_METADATA_FIELD_SET, name, value)

    def on_settings_updated(self, updated_settings):
        if "media_metadata" in updated_settings:
            self.setMinimumSize(settings.get("media_metadata", "window_width"), 0)

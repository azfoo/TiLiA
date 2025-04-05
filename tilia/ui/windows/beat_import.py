from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
)
from typing import Optional

from tilia.requests import get, Get


class GetScorePart(QDialog):
    def __init__(self, part_data: dict[str, tuple[str, list[str]]]):
        super().__init__(get(Get.MAIN_WINDOW))
        self.setWindowTitle("Select score part to import from")
        self.setLayout(QFormLayout())

        self.part_data = part_data

        header = QLabel("Please select the score part and staff:")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout().addRow(header)

        self.part_combo = QComboBox()
        self.part_combo.addItems([part[0] for part in self.part_data.values()])
        self.part_combo.setCurrentIndex(0)
        self.part_combo.currentIndexChanged.connect(self.update_staff_combo)
        self.layout().addRow(QLabel("Part Name:"), self.part_combo)

        self.staff_combo = QComboBox()
        self.staff_combo.addItems(self.__get_values_from_index(0)[1])
        self.layout().addRow(QLabel("Staff Number:"), self.staff_combo)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.layout().addRow(button_box)

    def update_staff_combo(self, current_part_index: int):
        self.staff_combo.clear()
        self.staff_combo.addItems(self.__get_values_from_index(current_part_index)[1])

    def __get_values_from_index(self, current_part_index: int) -> tuple[str, list[str]]:
        return [*self.part_data.values()][current_part_index]

    def get_result(self) -> tuple[str, str]:
        return [*self.part_data.keys()][
            self.part_combo.currentIndex()
        ], self.staff_combo.currentText()

    @classmethod
    def select(
        cls, part_data: dict[str, tuple[str, list[str]]]
    ) -> tuple[bool, Optional[tuple[str, str]]]:
        instance = cls(part_data)
        if instance.exec() == QDialog.DialogCode.Accepted:
            return True, instance.get_result()
        else:
            return False, None

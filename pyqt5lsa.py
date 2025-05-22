import sys
import xml.etree.ElementTree as ET
import numpy as np
from datetime import datetime
from scipy.linalg import solveh_banded
from numpy.testing import assert_almost_equal
import logging

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeView, QTextEdit, QMenuBar, QMenu, QAction, QFileDialog,
    QSplitter, QLabel, QPushButton, QScrollArea, QAbstractItemView,
    QStyle, QMessageBox, QComboBox
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QFont, QIcon, QTextOption
from PyQt5.QtCore import Qt, QSize

from strudbpkg.structuraldb import StructuralDatabase

class QTextEditLogger(QMainWindow):
    def __init__(self, text_edit: QTextEdit):
        super().__init__()
        self.text_edit = text_edit

    def emit(self, record):
        msg = self.format(record)
        self.text_edit.append(msg)

class MainWindow(QMainWindow):
    def __init__(self, db: StructuralDatabase):
        super().__init__()
        self.db = db
        #self.setStyleSheet("background-color: #111111; color: #78909C;")
        self.setGeometry(100, 100, 1000, 700)
        # Keep track of the file you opened (or saved to)
        self.current_file: str = ''
        self.is_modified = False

    # def initializeUI(self):
        screen = QApplication.primaryScreen().size()
        factor = 1.5
        new_width = int(screen.width() / factor)
        new_height = int(screen.height() / factor)
        self.resize(new_width, new_height)

    # def initUI(self):
        #self.setGeometry(100, 100, 1000, 700)
        self.setWindowTitle("EV Consulting Inc.")
        from PyQt5.QtGui import QIcon
        self.setWindowIcon(QIcon("evcilogop.jpg"))

        self.setStyleSheet("""
            QMainWindow {
                background-color: #111111; /* Dark brilliant black */
                color: #78909C /* Keeps text color white */
            }
            QMenuBar, QMenu {
                background-color: #2e2e2e;
                color: #78909C;
            }
            QTreeView, QTextEdit {
                background-color: #1e1e1e;
                color: #cccccc;
                border: 1px solid #3e3e3e;
                font-family: 'Courier';
                font-size: 16pt;
            }
            QScrollArea {
                border: none;
            }
            QLabel {
                color: #ffffff;
            }
            QPushButton {
                background-color: #3e3e3e;
                color: #ffffff;
                border: none;
            }
            QPushButton:hover {
                background-color: #5e5e5e;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background: #3e3e3e;
                width: 10px;  /* Set a smaller width for vertical scroll bars */
                height: 10px;  /* Set a smaller height for horizontal scroll bars */
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background: #888;
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                background: #2e2e2e;
                border: none;
            }
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical,
            QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {
                background: #2e2e2e;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none.
            }
        """)
        common_font = QFont("Courier", 16)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        self.banner_label = QLabel("Structural Analysis of Frames, Trusses and Grids")
        self.banner_label.setFont(QFont("Arial", 16))   
        self.banner_label.setAlignment(Qt.AlignCenter)
        self.banner_label.setStyleSheet("color: #007ACC;")
        main_layout.addWidget(self.banner_label)

        title_bar_layout = QHBoxLayout()
        main_layout.addLayout(title_bar_layout)

        title_label = QLabel("Selected Analysis Type")
        title_label.setFont(QFont("Arial", 20))
        title_bar_layout.addWidget(title_label, alignment=Qt.AlignLeft)
        
        self.analysis_type_combo = QComboBox()
        self.analysis_type_combo.addItems([
            "Static Linear Analysis",
            "Static Nonlinear Analysis",
            "Dynamic Linear Analysis",
            "Dynamic Nonlinear Analysis",
            "Frequency Domain Analysis",
            "Buckling Analysis"
        ])
        self.analysis_type_combo.setCurrentIndex(0)
        title_bar_layout.addWidget(self.analysis_type_combo, alignment=Qt.AlignRight)        

        style = QApplication.instance().style()

        open_icon = style.standardIcon(QStyle.SP_DialogOpenButton)
        save_icon = style.standardIcon(QStyle.SP_DialogSaveButton)
        exit_icon = style.standardIcon(QStyle.SP_DialogCloseButton)
        help_icon = style.standardIcon(QStyle.SP_DialogHelpButton)
        
        open_action = QAction(open_icon, "Open…", self)
        open_action.triggered.connect(self.open_file)
        exit_action = QAction(exit_icon, "Exit", self)
        exit_action.triggered.connect(self.close)
        run_icon = style.standardIcon(QStyle.SP_MediaPlay)

        # region buttons
        open_button = QPushButton()
        open_button.setIcon(open_icon)
        open_button.setIconSize(QSize(30, 30))
        open_button.clicked.connect(self.open_file)
        open_button.setToolTip("Open XML File")
        title_bar_layout.addWidget(open_button, alignment=Qt.AlignRight)

        self.save_button = QPushButton()
        self.save_button.setIcon(save_icon)
        self.save_button.setIconSize(QSize(30, 30))
        self.save_button.clicked.connect(self.save_file)
        self.save_button.setToolTip("Save XML File")
        self.save_button.setEnabled(False)
        title_bar_layout.addWidget(self.save_button, alignment=Qt.AlignRight)

        close_button = QPushButton()
        close_button.setIcon(exit_icon)
        close_button.setIconSize(QSize(30, 30))
        close_button.clicked.connect(self.close)
        close_button.setToolTip("Exit Program")
        title_bar_layout.addWidget(close_button, alignment=Qt.AlignRight)

        run_button = QPushButton()
        run_button.setIcon(run_icon)
        run_button.setIconSize(QSize(30, 30))
        #run_button.clicked.disconnect()  # Remove previous connection if any
        run_button.clicked.connect(self.run_selected_analysis)
        run_button.setToolTip("Run Analysis")
        
        # endregion buttons
        
        title_bar_layout.addWidget(run_button, alignment=Qt.AlignRight)

        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)

        top_frame = QWidget()
        bottom_frame = QWidget()
        splitter.addWidget(top_frame)
        splitter.addWidget(bottom_frame)

        top_layout = QHBoxLayout(top_frame)
        
        # region container
        
        tree_label = QLabel("XML Structure")
        xml_label = QLabel("XML Input")
        analysis_label = QLabel("Input Verification")
        
        tree_label.setFont(common_font)
        xml_label.setFont(common_font)
        analysis_label.setFont(common_font)    

        tree_container = QWidget()
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.addWidget(tree_label)
        self.tree_view = QTreeView()
        self.tree_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree_view.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(["XML Structure"])
        self.tree_view.setModel(self.tree_model)
        self.tree_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.setFont(common_font)
        self.tree_view.header().hide()  # Hide the redundant header
        
        
        tree_scroll_area = QScrollArea()
        tree_scroll_area.setWidgetResizable(True)
        tree_scroll_area.setWidget(self.tree_view)
        tree_layout.addWidget(tree_scroll_area)
        top_layout.addWidget(tree_container)

        # XML text container
        self.xml_container = QWidget(self)
        xml_layout = QVBoxLayout(self.xml_container)
        xml_layout.addWidget(xml_label)
        self.xml_text = QTextEdit()
        self.xml_text.setWordWrapMode(QTextOption.NoWrap)  # <-- Add this line
        self.xml_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.xml_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.xml_text.setFont(common_font)
        # self.xml_container.textChanged.connect(self.on_text_changed)
        # Detect user edits via textChanged
        self.xml_text.textChanged.connect(self.on_text_changed)
        xml_scroll_area = QScrollArea()
        xml_scroll_area.setWidgetResizable(True)
        xml_scroll_area.setWidget(self.xml_text)
        xml_layout.addWidget(xml_scroll_area)
        top_layout.addWidget(self.xml_container)
        

        analysis_container = QWidget()

        analysis_layout = QVBoxLayout(analysis_container)
        analysis_layout.addWidget(analysis_label)
        self.analysis_text = QTextEdit()
        self.analysis_text.setWordWrapMode(QTextOption.NoWrap) 
        self.analysis_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.analysis_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.analysis_text.setFont(common_font)
        analysis_scroll_area = QScrollArea()
        analysis_scroll_area.setWidgetResizable(True)
        analysis_scroll_area.setWidget(self.analysis_text)
        analysis_layout.addWidget(analysis_scroll_area)
        top_layout.addWidget(analysis_container)

        # endregion container
        

        bottom_layout = QVBoxLayout(bottom_frame)
        log_label = QLabel("Log Output")
        log_label.setFont(common_font)
        self.log_text = QTextEdit()
        self.log_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.log_text.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.log_text.setFont(common_font)
        log_scroll_area = QScrollArea()
        log_scroll_area.setWidgetResizable(True)
        log_scroll_area.setWidget(self.log_text)
        bottom_layout.addWidget(log_label)
        bottom_layout.addWidget(log_scroll_area)

        menu_bar = self.menuBar()
        self.setMenuBar(menu_bar)

        file_menu = QMenu("File", self)
        menu_bar.addMenu(file_menu)
        menu_bar.setStyleSheet("QMenuBar { background-color: #2e2e2e; }")
        menu_bar.setFont(QFont("Arial", 12))

        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        run_menu = QMenu("Run", self)
        menu_bar.addMenu(run_menu)

        run_action = QAction("Run Analysis", self)
        run_action.triggered.connect(self.run_selected_analysis)
        run_menu.addAction(run_action)

        # analysis_action = QAction("Analysis", self)
        # analysis_action.triggered.connect(self.run_analysis)
        # run_menu.addAction(analysis_action)
        
        display_menu = QMenu("Display", self)
        menu_bar.addMenu(display_menu)
        
        wire3d_action = QAction("Wireframe 3D", self)
        wire3d_action.triggered.connect(self.display_wireframe)
        display_menu.addAction(wire3d_action)

    def on_text_changed(self):
        # User has edited the text container
        if not self.is_modified:
            self.is_modified = True
        self.save_button.setEnabled(True)

    def open_file(self):
        """Open an XML file and display its content in the XML text area"""
        filename, _ = QFileDialog.getOpenFileName(self, "Open XML File", "", "XML Files (*.xml);;All Files (*)")
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8-sig') as file:
                    file_content = file.read()
                # Validate XML before proceeding
                try:
                    ET.fromstring(file_content)
                except ET.ParseError as e:
                    QMessageBox.critical(self, 'Open Error', f'Invalid XML format:\n{e}')
                    return

                self.tree_model.clear()
                self.tree_model.setHorizontalHeaderLabels(["XML Structure"])
                self.parse_xml_file(filename)
                self.current_file = filename
                self.xml_text.setText(file_content)
                self.db.xml_reader(filename)

                index = filename.index('.')
                self.db.results_file = filename[:index] + '_results.txt'
            except Exception as e:
                QMessageBox.critical(self, 'Open Error', str(e))
            
    def save_file(self):
        if not self.current_file or not self.is_modified:
            return
        text = self.xml_text.toPlainText()
        # Validate XML before saving
        try:
            ET.fromstring(text)
        except ET.ParseError as e:
            QMessageBox.critical(self, 'Save Error', f'Invalid XML format:\n{e}')
            return
        try:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(text)
            self.xml_text.document().setModified(False)
            self.is_modified = False  # Reset modification flag
            self.save_button.setEnabled(False)  # Disable after save            
            QMessageBox.information(self, 'Save', f'Saved {self.current_file}')
        except Exception as e:
            QMessageBox.critical(self, 'Save Error', str(e))    

    def parse_xml_file(self, filename):
        """Parse the XML file and display its content in the tree view"""
        tree_xml = ET.parse(filename)
        root_elem = tree_xml.getroot()
        self.insert_tree_items(self.tree_model.invisibleRootItem(), root_elem)
        self.tree_view.expandAll()

    def insert_tree_items(self, parent, element):
        """Recursively insert items into the tree view"""
        node = QStandardItem(element.tag)
        parent.appendRow(node)
        if element.text and element.text.strip():
            for line in element.text.strip().split('\n'):
                node.appendRow(QStandardItem(line))
        for child in element:
            self.insert_tree_items(node, child)

    # def run_analysis(self):
    #     """Run the structural analysis"""
    #     self.analysis_text.append("Running analysis...\n")
    #     self.db.k_assem()
    #     self.analysis_text.append("Stiffness matrix completed...\n")
    #     with open("stiff_output.txt", "w") as file:
    #         for i in range(self.db.ne):
    #             elst = self.db.stored_elst_matrices[i]
    #             file.write(f"Element: {i+1}\n{elst}")
    #         self.db.bound3()
    #         file.write("tk matrix:\n")
    #         file.write(f"{self.db.tk}")
    #         file.write("al matrix:\n")
    #         file.write(f"{self.db.al}")
    #     self.analysis_text.append("Solver started...\n")
    #     start_time = datetime.now()
    #     save_tk = self.db.tk.copy()
    #     save_al = self.db.al.copy()
    #     self.db.bgaussgen(self.db.tk, self.db.al)
    #     end_time = datetime.now()
    #     execution_time = end_time - start_time
    #     self.analysis_text.append(f"Solver finished Time: {execution_time.total_seconds() * 1000:.2f} milliseconds\n")
    #     ab = save_tk.T
    #     al_scipy = solveh_banded(ab, save_al, lower=True)
    #     try:
    #         assert_almost_equal(self.db.al.flatten(), al_scipy, decimal=6)
    #     except AssertionError:
    #         self.db.al = al_scipy.reshape(self.db.al.shape)
    #     self.db.forcegen()
    #     self.db.outptgen(self.db.results_file)
    #     with open(self.db.results_file, "r") as f:
    #         data = f.read()
    #         self.log_text.setText(data)
            
    def display_wireframe(self):
        """Display the wireframe 3D plot"""
        self.analysis_text.append("Displaying wireframe 3D plot...\n")
        self.db.plot_wire3d(is_3d=True)

    def close_window(self):
        self.close()

    def minimize_window(self):
        self.showMinimized()

    def setup_logging(self):
        """Setup logging for the application"""
        logTextBox = QTextEditLogger(self.analysis_text)
        logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logging.getLogger().addHandler(logTextBox)
        logging.getLogger().setLevel(logging.INFO)
        
    def run_selected_analysis(self):
        anal_type = self.analysis_type_combo.currentText()
        if anal_type == "Static Linear Analysis":
            self.run_static_linear()
        elif anal_type == "Static Nonlinear Analysis":
            self.run_static_nonlinear()
        elif anal_type == "Dynamic Linear Analysis":
            self.run_dynamic_linear()
        elif anal_type == "Dynamic Nonlinear Analysis":
            self.run_dynamic_nonlinear()
        elif anal_type == "Frequency Domain Analysis":
            self.run_frequency_domain()
        elif anal_type == "Buckling Analysis":
            self.run_buckling()
        else:
            QMessageBox.warning(self, "Analysis", "Unknown analysis type selected.")

    def run_static_linear(self):
        log_file = "analysis.log"
        self.db.run_analysis(log_file=log_file)
        with open(log_file, "r") as log:
            self.analysis_text.setText(log.read())
        with open(self.db.results_file, "r") as f:
            data = f.read()
            self.log_text.setText(data)

    def run_static_nonlinear(self):
        QMessageBox.information(self, "Not Implemented", "Static Nonlinear Analysis is not yet implemented.")

    def run_dynamic_linear(self):
        QMessageBox.information(self, "Not Implemented", "Dynamic Linear Analysis is not yet implemented.")

    def run_dynamic_nonlinear(self):
        QMessageBox.information(self, "Not Implemented", "Dynamic Nonlinear Analysis is not yet implemented.")

    def run_frequency_domain(self):
        QMessageBox.information(self, "Not Implemented", "Frequency Domain Analysis is not yet implemented.")

    def run_buckling(self):
        QMessageBox.information(self, "Not Implemented", "Buckling Analysis is not yet implemented.")                        

def main():
    app = QApplication(sys.argv)
    db=StructuralDatabase()
    main_window = MainWindow(db)
    main_window.show()
    sys.exit(app.exec_())

    db.connect()

if __name__ == "__main__":
    main()

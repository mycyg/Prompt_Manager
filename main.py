import sys
import re
import json
import os
import numpy as np
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QListWidget, QTextEdit, QLineEdit, QPushButton, QLabel, QSplitter,
    QMessageBox, QInputDialog, QDialog, QFormLayout, QDialogButtonBox,
    QListWidgetItem, QFrame, QFileDialog, QStatusBar, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QClipboard, QAction, QTextCursor, QMouseEvent

import database
import llm_client

CONFIG_FILE = 'config.json'

class TagLabel(QLabel):
    doubleClicked = Signal(str)
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setText(text)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.doubleClicked.emit(self.text())
        super().mouseDoubleClickEvent(event)

class OptimizeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自定义 AI 优化指令")
        self.layout = QVBoxLayout(self)
        self.instructions_edit = QTextEdit(self)
        self.instructions_edit.setText("你是一个提示词工程专家。请优化以下提示词，使其更清晰、更强大、更通用。请直接返回优化后的提示词内容，无需任何解释。")
        self.layout.addWidget(QLabel("编辑用于本次优化的指令:"))
        self.layout.addWidget(self.instructions_edit)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)

    def get_instructions(self):
        return self.instructions_edit.toPlainText()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API 设置")
        self.layout = QFormLayout(self)
        self.base_url_input = QLineEdit(self)
        self.api_key_input = QLineEdit(self)
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.model_input = QLineEdit(self)
        self.layout.addRow(QLabel("<b>LLM (生成/优化)</b>"))
        self.layout.addRow("LLM API Base URL:", self.base_url_input)
        self.layout.addRow("LLM API Key:", self.api_key_input)
        self.layout.addRow("LLM 模型名称:", self.model_input)
        self.embedding_base_url_input = QLineEdit(self)
        self.embedding_api_key_input = QLineEdit(self)
        self.embedding_api_key_input.setEchoMode(QLineEdit.Password)
        self.embedding_model_input = QLineEdit(self)
        self.layout.addRow(QLabel("<b>Embedding (语义搜索)</b>"))
        self.layout.addRow("Embedding API Base URL:", self.embedding_base_url_input)
        self.layout.addRow("Embedding API Key:", self.embedding_api_key_input)
        self.layout.addRow("Embedding 模型名称:", self.embedding_model_input)
        self.buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel, self)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        self.layout.addWidget(self.buttons)
        self.load_settings()

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.base_url_input.setText(config.get('base_url', ''))
                self.api_key_input.setText(config.get('api_key', ''))
                self.model_input.setText(config.get('model', ''))
                self.embedding_base_url_input.setText(config.get('embedding_base_url', ''))
                self.embedding_api_key_input.setText(config.get('embedding_api_key', ''))
                self.embedding_model_input.setText(config.get('embedding_model', ''))
            except (json.JSONDecodeError, IOError):
                pass

    def get_settings(self):
        return {
            'base_url': self.base_url_input.text(),
            'api_key': self.api_key_input.text(),
            'model': self.model_input.text(),
            'embedding_base_url': self.embedding_base_url_input.text(),
            'embedding_api_key': self.embedding_api_key_input.text(),
            'embedding_model': self.embedding_model_input.text(),
        }

    def load_settings(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.base_url_input.setText(config.get('base_url', ''))
                self.api_key_input.setText(config.get('api_key', ''))
                self.model_input.setText(config.get('model', ''))
                self.embedding_base_url_input.setText(config.get('embedding_base_url', ''))
                self.embedding_api_key_input.setText(config.get('embedding_api_key', ''))
                self.embedding_model_input.setText(config.get('embedding_model', ''))
            except (json.JSONDecodeError, IOError):
                pass

    def get_settings(self):
        return {
            'base_url': self.base_url_input.text(),
            'api_key': self.api_key_input.text(),
            'model': self.model_input.text(),
            'embedding_base_url': self.embedding_base_url_input.text(),
            'embedding_api_key': self.embedding_api_key_input.text(),
            'embedding_model': self.embedding_model_input.text(),
        }

class HistoryDialog(QDialog):
    version_restored = Signal(str)
    def __init__(self, prompt_id, parent=None):
        super().__init__(parent)
        self.setWindowTitle("历史版本")
        self.prompt_id = prompt_id
        self.setGeometry(150, 150, 800, 500)
        layout = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        self.version_list = QListWidget()
        self.version_list.currentItemChanged.connect(self.display_version_content)
        splitter.addWidget(self.version_list)
        self.content_preview = QTextEdit()
        self.content_preview.setReadOnly(True)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(self.content_preview)
        button_layout = QHBoxLayout()
        restore_button = QPushButton("恢复此版本")
        restore_button.clicked.connect(self.restore_version)
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(restore_button)
        button_layout.addWidget(close_button)
        right_layout.addLayout(button_layout)
        splitter.addWidget(right_widget)
        layout.addWidget(splitter)
        self.load_versions()

    def load_versions(self):
        versions = database.get_prompt_versions(self.prompt_id)
        for version in versions:
            item = QListWidgetItem(f"保存于: {version['saved_at']}")
            item.setData(Qt.UserRole, version['id'])
            self.version_list.addItem(item)

    def display_version_content(self, current, previous):
        if not current:
            return
        version_id = current.data(Qt.UserRole)
        content = database.get_version_content(version_id)
        if content:
            self.content_preview.setText(content)

    def restore_version(self):
        current_item = self.version_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个要恢复的版本。")
            return
        content = self.content_preview.toPlainText()
        self.version_restored.emit(content)
        self.accept()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("提示词管理工具")
        self.setGeometry(100, 100, 1400, 800)
        self.current_tags = []
        self.variable_inputs = {}
        self.is_dirty = False

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Top Bar ---
        top_bar_layout = QHBoxLayout()
        self.semantic_search_input = QLineEdit()
        self.semantic_search_input.setPlaceholderText("输入您的问题或需求进行语义搜索...")
        semantic_search_button = QPushButton("语义搜索")
        semantic_search_button.clicked.connect(self.perform_semantic_search)
        top_bar_layout.addWidget(QLabel("<b>智能检索:</b>"))
        top_bar_layout.addWidget(self.semantic_search_input)
        top_bar_layout.addWidget(semantic_search_button)
        top_bar_layout.addStretch()
        self.history_button = QPushButton("查看历史")
        self.history_button.clicked.connect(self.show_history)
        self.settings_button = QPushButton("设置")
        self.settings_button.clicked.connect(self.open_settings)
        top_bar_layout.addWidget(self.history_button)
        top_bar_layout.addWidget(self.settings_button)
        main_layout.addLayout(top_bar_layout)

        # --- Main 3-Pane Splitter ---
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)

        # --- Left Panel ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("按标题或标签筛选...")
        self.search_input.textChanged.connect(self.filter_prompts)
        left_layout.addWidget(QLabel("筛选列表"))
        left_layout.addWidget(self.search_input)
        self.prompt_list = QListWidget()
        self.prompt_list.currentItemChanged.connect(self.display_prompt_content)
        left_layout.addWidget(QLabel("提示词列表"))
        left_layout.addWidget(self.prompt_list)
        list_mgmt_layout = QGridLayout()
        new_prompt_button = QPushButton("新建")
        new_prompt_button.clicked.connect(self.create_new_prompt)
        delete_prompt_button = QPushButton("删除")
        delete_prompt_button.clicked.connect(self.delete_current_prompt)
        import_button = QPushButton("导入TXT")
        import_button.clicked.connect(self.import_from_txt)
        export_button = QPushButton("导出TXT")
        export_button.clicked.connect(self.export_to_txt)
        list_mgmt_layout.addWidget(new_prompt_button, 0, 0)
        list_mgmt_layout.addWidget(delete_prompt_button, 0, 1)
        list_mgmt_layout.addWidget(import_button, 1, 0)
        list_mgmt_layout.addWidget(export_button, 1, 1)
        left_layout.addLayout(list_mgmt_layout)
        main_splitter.addWidget(left_widget)

        # --- Center & Right Panel in a nested splitter ---
        right_side_splitter = QSplitter(Qt.Horizontal)

        # --- Center Panel (Editor) ---
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        self.prompt_title_input = QLineEdit()
        self.prompt_title_input.setPlaceholderText("提示词标题")
        self.prompt_title_input.textChanged.connect(self.mark_dirty)
        center_layout.addWidget(self.prompt_title_input)

        editor_splitter = QSplitter(Qt.Horizontal)
        template_widget = QWidget()
        template_layout = QVBoxLayout(template_widget)
        template_layout.setContentsMargins(0,0,0,0)
        template_layout.addWidget(QLabel("<b>模板编辑区</b>"))
        self.prompt_content_edit = QTextEdit()
        self.prompt_content_edit.setPlaceholderText("在此输入提示词模板... 输入 / 可快速插入变量")
        self.prompt_content_edit.textChanged.connect(self.on_template_change)
        template_layout.addWidget(self.prompt_content_edit)
        
        template_actions_layout = QHBoxLayout()
        insert_var_button = QPushButton("插入变量")
        insert_var_button.clicked.connect(self.insert_variable)
        save_button = QPushButton("立即保存")
        save_button.clicked.connect(self.save_prompt)
        ai_generate_button = QPushButton("AI 生成")
        ai_generate_button.clicked.connect(self.generate_prompt_with_ai)
        ai_optimize_button = QPushButton("AI 优化")
        ai_optimize_button.clicked.connect(self.optimize_prompt_with_ai)
        template_actions_layout.addWidget(insert_var_button)
        template_actions_layout.addWidget(save_button)
        template_actions_layout.addStretch()
        template_actions_layout.addWidget(ai_generate_button)
        template_actions_layout.addWidget(ai_optimize_button)
        template_layout.addLayout(template_actions_layout)

        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        preview_layout.setContentsMargins(0,0,0,0)
        preview_layout.addWidget(QLabel("<b>实时预览区</b>"))
        self.preview_edit = QTextEdit()
        self.preview_edit.setPlaceholderText("最终提示词预览")
        self.preview_edit.setReadOnly(True)
        preview_layout.addWidget(self.preview_edit)
        copy_button = QPushButton("一键复制结果")
        copy_button.clicked.connect(self.copy_prompt)
        preview_layout.addWidget(copy_button)

        editor_splitter.addWidget(template_widget)
        editor_splitter.addWidget(preview_widget)
        center_layout.addWidget(editor_splitter)

        tags_group = QWidget()
        tags_group.setMaximumHeight(100)
        tags_layout = QVBoxLayout(tags_group)
        tags_layout.setContentsMargins(0, 5, 0, 5)
        tags_header_layout = QHBoxLayout()
        tags_header_layout.addWidget(QLabel("标签 (双击编辑)"))
        tags_header_layout.addStretch()
        self.tags_display_widget = QWidget()
        self.tags_display_layout = QHBoxLayout(self.tags_display_widget)
        self.tags_display_layout.setContentsMargins(0,0,0,0)
        self.tags_display_layout.setAlignment(Qt.AlignLeft)
        tags_header_layout.addWidget(self.tags_display_widget)
        add_tag_layout = QHBoxLayout()
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("输入新标签后按Enter...")
        self.tag_input.returnPressed.connect(self.add_tag_from_input)
        add_tag_button = QPushButton("添加")
        add_tag_button.clicked.connect(self.add_tag_from_input)
        add_tag_layout.addWidget(self.tag_input)
        add_tag_layout.addWidget(add_tag_button)
        tags_layout.addLayout(tags_header_layout)
        tags_layout.addLayout(add_tag_layout)
        center_layout.addWidget(tags_group)
        right_side_splitter.addWidget(center_widget)

        # --- Right Panel ---
        self.right_panel_widget = QWidget()
        self.variable_layout = QFormLayout(self.right_panel_widget)
        self.right_panel_widget.setVisible(False)
        right_side_splitter.addWidget(self.right_panel_widget)
        
        main_splitter.addWidget(right_side_splitter)
        main_splitter.setSizes([250, 1150])
        right_side_splitter.setSizes([800, 350])

        self.setStatusBar(QStatusBar(self))

        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.setInterval(60000)
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.start()

        database.init_db()
        self.refresh_prompt_list()

    def mark_dirty(self):
        self.is_dirty = True
        self.statusBar().showMessage("有未保存的更改...", 3000)

    def on_template_change(self):
        self.mark_dirty()
        cursor = self.prompt_content_edit.textCursor()
        if cursor.position() > 0:
            try:
                char_before = self.prompt_content_edit.toPlainText()[cursor.position()-1]
                if char_before == '/':
                    cursor.deletePreviousChar()
                    self.prompt_content_edit.setTextCursor(cursor)
                    QTimer.singleShot(0, self.insert_variable)
            except IndexError:
                pass
        self.detect_variables()
        self.update_preview()

    def auto_save(self):
        if self.is_dirty:
            self.save_prompt(silent=True)

    def save_prompt(self, silent=False):
        prompt_id = self.get_current_prompt_id()
        if not prompt_id:
            if not silent:
                QMessageBox.warning(self, "警告", "没有选中要保存的提示词。")
            return
        title = self.prompt_title_input.text()
        content = self.prompt_content_edit.toPlainText()
        embedding = None
        try:
            if content.strip():
                embedding = llm_client.get_embedding(content)
                embedding = np.array(embedding, dtype=np.float32)
        except Exception as e:
            if not silent:
                QMessageBox.warning(self, "Embedding 错误", f"无法生成向量: {e}")
        database.update_prompt(prompt_id, title, content, embedding)
        database.update_prompt_tags(prompt_id, self.current_tags)
        current_item = self.prompt_list.currentItem()
        if current_item:
            current_item.setText(title)
        self.is_dirty = False
        msg = "已自动保存。" if silent else "提示词及标签已保存！"
        if embedding is not None:
            msg += " (向量已生成)"
        self.statusBar().showMessage(msg, 5000)

    def perform_semantic_search(self):
        query = self.semantic_search_input.text()
        if not query.strip():
            self.refresh_prompt_list()
            return
        try:
            self.statusBar().showMessage("正在生成查询向量...")
            QApplication.processEvents()
            query_embedding = llm_client.get_embedding(query)
            query_embedding = np.array(query_embedding, dtype=np.float32)
            self.statusBar().showMessage("正在进行语义搜索...")
            QApplication.processEvents()
            sorted_ids = database.semantic_search_prompts(query_embedding)
            if not sorted_ids:
                QMessageBox.information(self, "未找到", "未找到语义相关的提示词。 সন")
                self.statusBar().clearMessage()
                return
            self.refresh_prompt_list(ids_ordered=sorted_ids)
            self.statusBar().showMessage(f"找到 {len(sorted_ids)} 个语义相关结果。", 5000)
        except Exception as e:
            QMessageBox.critical(self, "语义搜索错误", f"搜索失败: {e}")
            self.statusBar().clearMessage()

    def refresh_prompt_list(self, query="", ids_ordered=None):
        current_id = self.get_current_prompt_id()
        self.prompt_list.blockSignals(True)
        self.prompt_list.clear()
        if ids_ordered is not None:
            prompts = database.get_prompts_by_ids(ids_ordered)
        else:
            prompts = database.search_prompts(query)
        for i, prompt in enumerate(prompts):
            item = QListWidgetItem(prompt['title'])
            item.setData(Qt.UserRole, prompt['id'])
            self.prompt_list.addItem(item)
            if prompt['id'] == current_id:
                self.prompt_list.setCurrentRow(i)
        self.prompt_list.blockSignals(False)
        if self.prompt_list.count() > 0 and self.prompt_list.currentRow() == -1:
             self.prompt_list.setCurrentRow(0)

    def filter_prompts(self):
        query = self.search_input.text()
        self.refresh_prompt_list(query)

    def display_prompt_content(self, current, previous):
        if not current:
            self.prompt_title_input.clear()
            self.prompt_content_edit.clear()
            self.update_tags_display([], mark_dirty=False)
            self.detect_variables()
            self.update_preview()
            self.is_dirty = False
            return
        prompt_id = current.data(Qt.UserRole)
        prompt = database.get_prompt_details(prompt_id)
        if prompt:
            self.prompt_content_edit.blockSignals(True)
            self.prompt_title_input.blockSignals(True)
            self.prompt_title_input.setText(prompt['title'])
            self.prompt_content_edit.setText(prompt['content'])
            self.prompt_content_edit.blockSignals(False)
            self.prompt_title_input.blockSignals(False)
            self.current_tags = database.get_prompt_tags(prompt_id)
            self.update_tags_display(self.current_tags, mark_dirty=False)
            self.on_template_change()
            self.is_dirty = False

    def update_tags_display(self, tags, mark_dirty=True):
        if mark_dirty: self.mark_dirty()
        while self.tags_display_layout.count():
            child = self.tags_display_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for tag_name in tags:
            tag_widget = QWidget()
            tag_layout = QHBoxLayout(tag_widget)
            tag_layout.setContentsMargins(0,0,0,0)
            tag_label = TagLabel(tag_name)
            tag_label.doubleClicked.connect(self.edit_tag)
            tag_label.setObjectName("TagLabel")
            remove_button = QPushButton("x")
            remove_button.setFixedSize(20, 20)
            remove_button.clicked.connect(lambda checked=False, name=tag_name: self.remove_tag(name))
            tag_layout.addWidget(tag_label)
            tag_layout.addWidget(remove_button)
            self.tags_display_layout.addWidget(tag_widget)

    def add_tag_from_input(self):
        tag_name = self.tag_input.text().strip()
        if tag_name and tag_name not in self.current_tags:
            self.current_tags.append(tag_name)
            self.update_tags_display(self.current_tags)
            self.tag_input.clear()
    
    def remove_tag(self, tag_name):
        if tag_name in self.current_tags:
            self.current_tags.remove(tag_name)
            self.update_tags_display(self.current_tags)

    def edit_tag(self, old_name):
        new_name, ok = QInputDialog.getText(self, "编辑标签", "输入新的标签名称:", text=old_name)
        if ok and new_name and new_name.strip() != old_name:
            if new_name in self.current_tags:
                QMessageBox.warning(self, "错误", "该标签已存在。")
                return
            try:
                index = self.current_tags.index(old_name)
                self.current_tags[index] = new_name.strip()
                self.update_tags_display(self.current_tags)
            except ValueError:
                pass

    def get_current_prompt_id(self):
        current_item = self.prompt_list.currentItem()
        return current_item.data(Qt.UserRole) if current_item else None

    def create_new_prompt(self):
        title, ok = QInputDialog.getText(self, "新建提示词", "为新的提示词输入一个标题:")
        if ok and title:
            prompt_id = database.add_prompt(title, "")
            self.refresh_prompt_list()
            for i in range(self.prompt_list.count()):
                item = self.prompt_list.item(i)
                if item.data(Qt.UserRole) == prompt_id:
                    self.prompt_list.setCurrentItem(item)
                    break

    def delete_current_prompt(self):
        current_item = self.prompt_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请先选择一个要删除的提示词。")
            return
        reply = QMessageBox.question(self, '确认删除', f"您确定要永久删除提示词 '{current_item.text()}' 吗？\n此操作不可撤销。", QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            prompt_id = current_item.data(Qt.UserRole)
            database.delete_prompt(prompt_id)
            self.refresh_prompt_list()
            self.statusBar().showMessage(f"提示词 '{current_item.text()}' 已删除。", 5000)

    def copy_prompt(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.preview_edit.toPlainText())
        self.statusBar().showMessage("预览结果已复制到剪贴板！", 3000)

    def detect_variables(self):
        # Clear existing variable widgets and the tracking dictionary
        while self.variable_layout.count():
            child = self.variable_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.variable_inputs.clear()

        content = self.prompt_content_edit.toPlainText()
        variables = sorted(list(set(re.findall(r'{{(.+?)}}', content))))

        if not variables:
            self.right_panel_widget.setVisible(False)
            return

        self.right_panel_widget.setVisible(True)
        for var_name in variables:
            line_edit = QLineEdit()
            line_edit.textChanged.connect(self.update_preview)
            line_edit.textChanged.connect(self.mark_dirty)
            self.variable_layout.addRow(f"{{{{{var_name}}}}}", line_edit)
            self.variable_inputs[var_name] = line_edit

    def update_preview(self):
        template = self.prompt_content_edit.toPlainText()
        for var_name, input_widget in self.variable_inputs.items():
            template = template.replace(f'{{{{{var_name}}}}}', input_widget.text())
        self.preview_edit.setText(template)

    def insert_variable(self):
        var_name, ok = QInputDialog.getText(self, "插入变量", "输入变量名 (无需输入花括号): ")
        if ok and var_name:
            self.prompt_content_edit.insertPlainText(f'{{{{{var_name}}}}}')

    def show_history(self):
        prompt_id = self.get_current_prompt_id()
        if not prompt_id:
            QMessageBox.warning(self, "警告", "请先选择一个提示词以查看其历史记录。")
            return
        dialog = HistoryDialog(prompt_id, self)
        dialog.version_restored.connect(self.restore_from_history)
        dialog.exec()

    def restore_from_history(self, content):
        self.prompt_content_edit.setText(content)
        self.mark_dirty()
        QMessageBox.information(self, "成功", "已从历史版本恢复内容。")

    def open_settings(self):
        dialog = SettingsDialog(self)
        if dialog.exec():
            settings = dialog.get_settings()
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=4, ensure_ascii=False)
            self.statusBar().showMessage("API 设置已成功保存。", 3000)

    def _handle_llm_call(self, llm_function, *args):
        try:
            return llm_function(*args)
        except ValueError as e:
            QMessageBox.warning(self, "配置错误", str(e))
            self.open_settings()
            return None
        except RuntimeError as e:
            QMessageBox.critical(self, "API错误", str(e))
            return None

    def generate_prompt_with_ai(self):
        requirement, ok = QInputDialog.getText(self, "AI 生成提示词", "请输入您的需求：")
        if ok and requirement:
            self.statusBar().showMessage("正在请求 AI 生成提示词...")
            QApplication.processEvents()
            new_content = self._handle_llm_call(llm_client.generate_prompt, requirement)
            if new_content:
                self.prompt_content_edit.setText(new_content)
                self.statusBar().showMessage("AI 生成完成！", 5000)
            else:
                self.statusBar().clearMessage()

    def optimize_prompt_with_ai(self):
        current_content = self.prompt_content_edit.toPlainText()
        if not current_content.strip():
            QMessageBox.warning(self, "警告", "编辑器中没有内容可供优化。")
            return
        dialog = OptimizeDialog(self)
        if dialog.exec():
            instructions = dialog.get_instructions()
            self.statusBar().showMessage("正在请求 AI 优化提示词...")
            QApplication.processEvents()
            optimized_content = self._handle_llm_call(llm_client.optimize_prompt, current_content, instructions)
            if optimized_content:
                self.prompt_content_edit.setText(optimized_content)
                self.statusBar().showMessage("AI 优化完成！", 5000)
            else:
                self.statusBar().clearMessage()

    def import_from_txt(self):
        file_paths, _ = QFileDialog.getOpenFileNames(self, "选择要导入的TXT文件", "", "Text Files (*.txt)")
        if not file_paths:
            return
        imported_count = 0
        for path in file_paths:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                title = os.path.splitext(os.path.basename(path))[0]
                database.add_prompt(title, content)
                imported_count += 1
            except Exception as e:
                QMessageBox.warning(self, "导入错误", f"无法导入文件 {path}:\n{e}")
        if imported_count > 0:
            QMessageBox.information(self, "成功", f"{imported_count} 个提示词已成功导入。 সন")
            self.refresh_prompt_list()

    def export_to_txt(self):
        dir_path = QFileDialog.getExistingDirectory(self, "选择要导出到的文件夹")
        if not dir_path:
            return
        prompts = database.search_prompts()
        if not prompts:
            QMessageBox.information(self, "信息", "数据库中没有可导出的提示词。")
            return
        exported_count = 0
        for prompt_data in prompts:
            try:
                prompt_details = database.get_prompt_details(prompt_data['id'])
                safe_title = re.sub(r'[\\/*?"<>|]', "_", prompt_details['title'])
                file_path = os.path.join(dir_path, f"{safe_title}.txt")
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(prompt_details['content'])
                exported_count += 1
            except Exception as e:
                QMessageBox.warning(self, "导出错误", f"无法导出提示词 '{prompt_data['title']}':\n{e}")
        if exported_count > 0:
            QMessageBox.information(self, "成功", f"{exported_count} 个提示词已成功导出到文件夹:\n{dir_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    style_file = os.path.join(script_dir, "style.qss")
    try:
        with open(style_file, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())
    except FileNotFoundError:
        print(f"警告: 样式文件未找到于 {style_file}，将使用默认样式。")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

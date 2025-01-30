# ui/tabs/network_tab.py

from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QTextEdit, QFileDialog, QTreeWidget, QTreeWidgetItem,
                             QMessageBox, QHeaderView, QSplitter, QDialog, QLineEdit, QFormLayout)
from PySide6.QtCore import Qt
from PySide6.QtWebEngineWidgets import QWebEngineView
import json
import re
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parents[2]))

from utils.db import get_db
from .path_extractor import PathExtractor
from .network_db_ops import NetworkDatabaseOperations

class ProjectDialog(QDialog):
    """Dialog for creating or selecting a project."""
    def __init__(self, db_ops, parent=None):
        super().__init__(parent)
        self.db_ops = db_ops
        self.setup_ui()

    def setup_ui(self):
        """Setup the dialog UI components."""
        self.setWindowTitle("Create Project")
        layout = QFormLayout(self)
        
        # Set dialog size
        self.setMinimumWidth(400)
        
        # Project name input
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter project name")
        layout.addRow("Project Name:", self.name_input)

        # Description input
        self.desc_input = QTextEdit()  # Changed to QTextEdit for multiline support
        self.desc_input.setPlaceholderText("Enter project description")
        self.desc_input.setMaximumHeight(100)  # Limit height
        layout.addRow("Description:", self.desc_input)

        # Validation label (hidden by default)
        self.validation_label = QLabel()
        self.validation_label.setStyleSheet("color: red;")
        self.validation_label.hide()
        layout.addRow(self.validation_label)

        # Buttons
        button_layout = QHBoxLayout()
        
        self.create_btn = QPushButton("Create")
        self.create_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                padding: 5px 15px;
                border-radius: 3px;
            }
        """)
        
        self.create_btn.clicked.connect(self.validate_and_accept)
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.create_btn)
        layout.addRow(button_layout)

    def validate_and_accept(self):
        """Validate inputs before accepting the dialog."""
        project_name = self.name_input.text().strip()
        
        if not project_name:
            self.validation_label.setText("Project name is required!")
            self.validation_label.show()
            return
            
        if len(project_name) < 3:
            self.validation_label.setText("Project name must be at least 3 characters!")
            self.validation_label.show()
            return
            
        self.validation_label.hide()
        self.accept()

    def get_project_data(self) -> dict:
        """Get the project data from the dialog.
        
        Returns:
            dict: Dictionary containing project name and description
        """
        return {
            'name': self.name_input.text().strip(),
            'description': self.desc_input.toPlainText().strip()
        }

class NetworkTab(QWidget):
    
    def __init__(self):
        super().__init__()
        self.network_data = None
        self.components = {
            'DP': 'Distribution Point',
            'MC': 'Canal',
            'ZT': 'Gate',
            'SW': 'Smart Water',
            'F': 'Field'
        }
        self.connections = []
        self.node_labels = {}
        
        # Database integration
        self.db = next(get_db())
        self.db_ops = NetworkDatabaseOperations(self.db)
        self.current_project_id = None
        self.current_network_id = None
        
        self.setup_ui()

    def setup_ui(self):
        """Setup the tab's user interface."""
        layout = QVBoxLayout()
        layout.setSpacing(5)
        
        # Project section
        project_layout = QHBoxLayout()
        
        self.create_project_btn = QPushButton("Create Project")
        self.create_project_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 5px 15px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.create_project_btn.clicked.connect(self.create_project)
        
        self.project_label = QLabel("No project selected")
        self.project_label.setStyleSheet("font-weight: bold;")
        
        project_layout.addWidget(self.create_project_btn)
        project_layout.addWidget(self.project_label)
        project_layout.addStretch()
        
        layout.addLayout(project_layout)
        
        # Network controls section
        network_layout = QHBoxLayout()
        
        self.upload_btn = QPushButton("Upload Mermaid File")
        self.upload_btn.setEnabled(False)  # Disabled until project is created
        self.upload_btn.clicked.connect(self.upload_file)
        
        self.file_label = QLabel("No file selected")
        
        self.analyze_components_btn = QPushButton("1. Analyze Components")
        self.analyze_components_btn.clicked.connect(self.analyze_components)
        self.analyze_components_btn.setEnabled(False)
        
        network_layout.addWidget(self.upload_btn)
        network_layout.addWidget(self.file_label)
        network_layout.addWidget(self.analyze_components_btn)
        network_layout.addStretch()
        
        layout.addLayout(network_layout)
        
        # Content and Results section
        middle_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # File content preview
        self.content_preview = QTextEdit()
        self.content_preview.setReadOnly(True)
        self.content_preview.setPlaceholderText("Mermaid file content will appear here")
        middle_splitter.addWidget(self.content_preview)
        
        # Results tree
        self.results_tree = QTreeWidget()
        self.results_tree.setHeaderLabels(["Component Type", "ID", "Details"])
        self.results_tree.header().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        middle_splitter.addWidget(self.results_tree)
        
        # Add middle section to vertical splitter
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.addWidget(middle_splitter)
        
        # Path Analysis section
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        
        self.analyze_paths_btn = QPushButton("2. Analyze Paths")
        self.analyze_paths_btn.clicked.connect(self.analyze_paths)
        self.analyze_paths_btn.setEnabled(False)
        bottom_layout.addWidget(self.analyze_paths_btn)
        
        self.paths_display = QWebEngineView()
        self.paths_display.setMinimumHeight(400)
        bottom_layout.addWidget(self.paths_display)
        
        main_splitter.addWidget(bottom_widget)
        
        # Add the main splitter to the layout
        layout.addWidget(main_splitter)
        self.setLayout(layout)

    def create_project(self):
        """Open dialog to create a new project and save to database."""
        dialog = ProjectDialog(self.db_ops, self)
        if dialog.exec():
            try:
                project_data = dialog.get_project_data()
                project = self.db_ops.create_project(
                    name=project_data['name'],
                    description=project_data['description']
                )
                self.current_project_id = project.id
                self.project_label.setText(f"Project: {project.name}")
                self.upload_btn.setEnabled(True)
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Project '{project.name}' created successfully!"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to create project: {str(e)}"
                )

    def upload_file(self):
        """Upload and validate network file."""
        if not self.current_project_id:
            QMessageBox.warning(self, "Warning", "Please create a project first")
            return

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Mermaid File",
            "",
            "Mermaid Files (*.mmd *.txt);;All Files (*)"
        )
        
        if file_name:
            try:
                with open(file_name, 'r', encoding='utf-8') as file:
                    content = file.read()
                    
                    # Validate Mermaid content
                    if not self._validate_mermaid_content(content):
                        raise ValueError("Invalid Mermaid file format")
                    
                    self.network_data = content
                    self.file_label.setText(file_name.split('/')[-1])
                    self.content_preview.setText(content)
                    self.analyze_components_btn.setEnabled(True)
                    self.connections = []
                    self.node_labels.clear()
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error reading file: {str(e)}")

    def _validate_mermaid_content(self, content: str) -> bool:
        """Validate the Mermaid file content format."""
        # Check for basic Mermaid graph syntax
        if not content.strip():
            return False
            
        # Check for required components
        has_components = bool(re.search(r'\w+\["[^\]]+"\]', content))
        has_connections = bool(re.search(r'\w+\s*-+>\s*\w+', content))
        
        return has_components and has_connections

    def analyze_components(self):
        """Analyze network components and save to database."""
        if not self.network_data:
            return
        
        try:
            # Clear previous results
            self.results_tree.clear()
            self.connections.clear()
            self.node_labels.clear()
            
            # Extract components and build data structure
            components_data = {}
            extracted_components = re.findall(r'(\w+)\["([^\]]+)"\]', self.network_data)
            
            for component_id, component_label in extracted_components:
                component_type = re.match(r'[A-Za-z]+', component_id).group()
                
                if component_type in self.components:
                    if component_type not in components_data:
                        components_data[component_type] = {}
                    
                    components_data[component_type][component_id] = {
                        'label': component_label,
                        'properties': {}
                    }
                    self.node_labels[component_id] = component_label
            
            # Extract connections
            self.connections = re.findall(r'(\w+)\s*-+>\s*(\w+)', self.network_data)
            connections_list = [f"{source}--->{target}" for source, target in self.connections]
            
            # Save to database
            network = self.db_ops.save_network_structure(
                project_id=self.current_project_id,
                mermaid_content=self.network_data,
                components_data=components_data,
                connections=connections_list
            )
            self.current_network_id = network.id
            
            # Update UI
            self.update_results_tree(components_data)
            self.analyze_paths_btn.setEnabled(True)
            
            # Show success message
            component_counts = "\n".join(
                f"{self.components[ctype]}: {len(comps)}"
                for ctype, comps in sorted(components_data.items())
            )
            
            QMessageBox.information(
                self,
                "Success", 
                f"Network structure saved successfully!\n\n"
                f"Component counts:\n{component_counts}"
            )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error analyzing network: {str(e)}"
            )

    def update_results_tree(self, components_data: dict):
        """Update the results tree with analyzed component data."""
        self.results_tree.clear()
        
        for comp_type, components in sorted(components_data.items()):
            parent = QTreeWidgetItem(self.results_tree)
            parent.setText(0, self.components[comp_type])
            parent.setText(1, f"Total: {len(components)}")
            parent.setExpanded(True)
            
            for comp_id, details in sorted(components.items()):
                child = QTreeWidgetItem(parent)
                child.setText(0, self.components[comp_type])
                child.setText(1, comp_id)
                
                # Add label and connectivity information
                details_text = details['label']
                if comp_type == 'F':  # For Field components, show connections
                    predecessors = [src for src, tgt in self.connections if tgt == comp_id]
                    if predecessors:
                        details_text += f" (Connected to: {', '.join(predecessors)})"
                
                child.setText(2, details_text)

    def analyze_paths(self):
        """Analyze network paths and save results to database."""
        if not self.network_data or not self.current_network_id:
            return

        try:
            # Create path extractor and analyze
            connection_lines = [line.strip() for line in self.network_data.split('\n') 
                              if '-->' in line]
            
            path_extractor = PathExtractor(connection_lines)
            
            # Build connection maps
            outgoing_map = {}
            incoming_map = {}
            all_nodes = set()
            
            for conn in connection_lines:
                for source, target in path_extractor.extract_connections(conn):
                    all_nodes.add(source)
                    all_nodes.add(target)
                    
                    if source not in outgoing_map:
                        outgoing_map[source] = set()
                    outgoing_map[source].add(target)
                    
                    if target not in incoming_map:
                        incoming_map[target] = set()
                    incoming_map[target].add(source)
            
            # Find start and end points
            start_points = sorted([node for node in all_nodes if node not in incoming_map])
            end_points = sorted([node for node in all_nodes if node not in outgoing_map])
            
            # Find all paths
            path_extractor.find_all_paths(start_points, end_points)
            path_data = path_extractor.get_path_data()
            
            # Save analysis results
            self.db_ops.update_network_analysis(
                network_id=self.current_network_id,
                paths_data=path_data,
                diagnostics=path_extractor.diagnostics
            )
            
            # Update UI
            html_content = self.get_react_html(path_data)
            self.paths_display.setHtml(html_content)
            
            # Calculate and show statistics
            total_paths = sum(len(paths) for paths in path_extractor.paths.values())
            total_endpoints = len(end_points)
            endpoints_with_paths = sum(1 for paths in path_extractor.paths.values() if paths)
            
            if total_paths == 0:
                QMessageBox.warning(
                    self,
                    "Analysis Complete", 
                    f"No valid paths found from detected source points ({', '.join(start_points)}) "
                    f"to end points ({', '.join(end_points)}).\n"
                    "Please check the diagnostic information for details."
                )
                return
            
            # Calculate average path length
            path_lengths = [len(path) - 1 for paths in path_extractor.paths.values() 
                          for path in paths]
            avg_path_length = sum(path_lengths) / len(path_lengths) if path_lengths else 0
            
            QMessageBox.information(
                self,
                "Analysis Complete", 
                f"Found paths to {endpoints_with_paths} out of {total_endpoints} end points.\n"
                f"Start points detected: {', '.join(start_points)}\n"
                f"End points detected: {', '.join(end_points)}\n"
                f"Total number of unique paths: {total_paths}\n"
                f"Average path length: {avg_path_length:.1f} segments"
            )
                
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error analyzing paths: {str(e)}"
            )

    def get_react_html(self, path_data):
        """Generate HTML with React component and data."""
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <script src="https://cdnjs.cloudflare.com/ajax/libs/react/18.2.0/umd/react.production.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/react-dom/18.2.0/umd/react-dom.production.min.js"></script>
            <script src="https://cdnjs.cloudflare.com/ajax/libs/babel-standalone/7.23.5/babel.min.js"></script>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body>
            <div id="root"></div>
            <script type="text/babel">
                const pathData = {json.dumps(path_data)};
                
                {self.get_react_component()}
                
                ReactDOM.render(
                    React.createElement(PathSummaryDisplay, {{ data: pathData }}),
                    document.getElementById('root')
                );
            </script>
        </body>
        </html>
        '''

    def get_react_component(self):
        """Return the React component code as a string."""
        return '''
        function PathSummaryDisplay({ data }) {
            const [expandedPaths, setExpandedPaths] = React.useState({});
            const [expandedSections, setExpandedSections] = React.useState({
                diagnostics: true,
                paths: true
            });

            const toggleSection = (section) => {
                setExpandedSections(prev => ({
                    ...prev,
                    [section]: !prev[section]
                }));
            };

            const togglePath = (endPoint) => {
                setExpandedPaths(prev => ({
                    ...prev,
                    [endPoint]: !prev[endPoint]
                }));
            };

            const getNodeTypeClass = (node) => {
                if (node.startsWith('F')) return 'text-green-600';
                if (node.startsWith('MC')) return 'text-blue-600';
                if (node.startsWith('SW')) return 'text-purple-600';
                if (node.startsWith('ZT')) return 'text-orange-600';
                if (node.startsWith('DP')) return 'text-red-600';
                return 'text-gray-600';
            };

            return (
                <div className="w-full p-4 bg-white">
                    <h2 className="text-2xl font-bold mb-4">Path Analysis Results</h2>

                    {/* Diagnostics Section */}
                    {data.diagnostics.length > 0 && (
                        <div className="mb-6">
                            <div 
                                className="flex items-center cursor-pointer bg-gray-100 p-2 rounded"
                                onClick={() => toggleSection('diagnostics')}
                            >
                                <span className="transform transition-transform">
                                    {expandedSections.diagnostics ? '▼' : '▶'}
                                </span>
                                <h3 className="text-lg font-semibold ml-2">Diagnostic Information</h3>
                            </div>
                            
                            {expandedSections.diagnostics && (
                                <div className="mt-2 ml-6">
                                    {data.diagnostics.map((diagnostic, index) => (
                                        <div key={index} className="text-gray-700 mb-1">
                                            • {diagnostic}
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Paths Section */}
                    <div>
                        <div 
                            className="flex items-center cursor-pointer bg-gray-100 p-2 rounded"
                            onClick={() => toggleSection('paths')}
                        >
                            <span className="transform transition-transform">
                                {expandedSections.paths ? '▼' : '▶'}
                            </span>
                            <h3 className="text-lg font-semibold ml-2">Paths Found</h3>
                        </div>

                        {expandedSections.paths && (
                            <div className="mt-2">
                                {Object.entries(data.paths).map(([endPoint, paths]) => (
                                    <div key={endPoint} className="mb-4 ml-4">
                                        <div 
                                            className="flex items-center cursor-pointer hover:bg-gray-50 p-2"
                                            onClick={() => togglePath(endPoint)}
                                        >
                                            <span className="transform transition-transform">
                                                {expandedPaths[endPoint] ? '▼' : '▶'}
                                            </span>
                                            <span className="font-medium ml-2">
                                                Paths to {endPoint} ({paths.length} found)
                                            </span>
                                        </div>

                                        {expandedPaths[endPoint] && (
                                            <div className="ml-8">
                                                {paths.map((pathInfo, index) => (
                                                    <div key={index} className="mb-2">
                                                        <div className="font-medium text-sm text-gray-600 mb-1">
                                                            Path {index + 1} ({pathInfo.length} segments) - {pathInfo.type}
                                                        </div>
                                                        <div className="flex flex-wrap items-center">
                                                            {pathInfo.path.map((node, nodeIndex) => (
                                                                <React.Fragment key={nodeIndex}>
                                                                    <span className={`${getNodeTypeClass(node)}`}>
                                                                        {node}
                                                                    </span>
                                                                    {nodeIndex < pathInfo.path.length - 1 && (
                                                                        <span className="mx-2 text-gray-400">→</span>
                                                                    )}
                                                                </React.Fragment>
                                                            ))}
                                                        </div>
                                                    </div>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            );
        }
        '''


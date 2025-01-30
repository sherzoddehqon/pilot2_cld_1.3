# ui/tabs/network_db_ops.py

from sqlalchemy.orm import Session
from typing import Dict, List, Optional
import json
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parents[2]))

from utils.db import Project, NetworkStructure, NetworkComponent

class NetworkDatabaseOperations:
    def __init__(self, session: Session):
        self.session = session

    def create_project(self, name: str, description: Optional[str] = None) -> Project:
        """Create a new project."""
        project = Project(name=name, description=description)
        self.session.add(project)
        self.session.commit()
        return project

    def save_network_structure(
        self, 
        project_id: int, 
        mermaid_content: str,
        components_data: Dict,
        connections: List[str]
    ) -> NetworkStructure:
        """Save the network structure and its components to the database."""
        network = NetworkStructure(
            project_id=project_id,
            mermaid_content=mermaid_content,
            components_json=json.dumps(components_data),
            connections_json=json.dumps(connections)
        )
        self.session.add(network)
        self.session.commit()
        
        # Add individual components
        for comp_type, components in components_data.items():
            for comp_id, details in components.items():
                component = NetworkComponent(
                    network_id=network.id,
                    component_id=comp_id,
                    component_type=comp_type,
                    label=details.get('label', ''),
                    properties=json.dumps(details.get('properties', {}))
                )
                self.session.add(component)
        
        self.session.commit()
        return network

    def get_project_networks(self, project_id: int) -> List[NetworkStructure]:
        """Get all network structures for a project."""
        return self.session.query(NetworkStructure).filter(
            NetworkStructure.project_id == project_id
        ).all()

    def get_network_components(self, network_id: int) -> List[NetworkComponent]:
        """Get all components for a network structure."""
        return self.session.query(NetworkComponent).filter(
            NetworkComponent.network_id == network_id
        ).all()

    def update_network_analysis(
        self,
        network_id: int,
        paths_data: Dict,
        diagnostics: List[str]
    ) -> NetworkStructure:
        """Update network with analysis results."""
        network = self.session.query(NetworkStructure).get(network_id)
        if network:
            network.paths_json = json.dumps(paths_data)
            network.diagnostics_json = json.dumps(diagnostics)
            network.analysis_date = datetime.utcnow()
            self.session.commit()
        return network

    def get_latest_network(self, project_id: int) -> Optional[NetworkStructure]:
        """Get the most recently created network structure for a project."""
        return self.session.query(NetworkStructure).filter(
            NetworkStructure.project_id == project_id
        ).order_by(NetworkStructure.upload_date.desc()).first()
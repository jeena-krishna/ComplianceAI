import os
import chromadb
from chromadb.config import Settings
from typing import Optional, List, Dict, Any
from .license_data import LICENSE_DATABASE


class LicenseRAG:
    def __init__(self, persist_directory: str = "./chromadb_data"):
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)
        
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="license_info",
            metadata={"description": "License information for compliance checking"}
        )
        
        if self.collection.count() == 0:
            self._index_licenses()
    
    def _index_licenses(self):
        documents = []
        metadatas = []
        ids = []
        
        for license_id, data in LICENSE_DATABASE.items():
            doc = self._create_document(license_id, data)
            documents.append(doc)
            
            meta = {
                "spdx_id": data["spdx_id"],
                "name": data["name"],
                "osi_approved": str(data.get("osi_approved", False)),
                "fsf_free": str(data.get("fsf_free", False)),
            }
            metadatas.append(meta)
            ids.append(license_id)
        
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def _create_document(self, license_id: str, data: Dict[str, Any]) -> str:
        parts = [
            f"License: {data['name']} ({license_id})",
            f"Description: {data.get('description', '')}",
            f"Permissions: {', '.join(data.get('permissions', []))}",
            f"Conditions: {', '.join(data.get('conditions', []))}",
            f"Limitations: {', '.join(data.get('limitations', []))}",
            f"OSI Approved: {data.get('osi_approved', False)}",
            f"FSF Free: {data.get('fsf_free', False)}",
            f"Compatible with: {', '.join(data.get('compatibility', []))}",
        ]
        return " | ".join(parts)
    
    def search(self, query: str, n_results: int = 3) -> List[Dict[str, Any]]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        if not results["documents"] or not results["documents"][0]:
            return []
        
        output = []
        for i, doc in enumerate(results["documents"][0]):
            meta = results["metadatas"][0][i]
            output.append({
                "license_id": results["ids"][0][i],
                "document": doc,
                "metadata": meta,
            })
        return output
    
    def get_license(self, license_id: str) -> Optional[Dict[str, Any]]:
        results = self.collection.get(ids=[license_id])
        
        if not results["documents"]:
            return None
        
        return {
            "license_id": results["ids"][0],
            "document": results["documents"][0],
            "metadata": results["metadatas"][0],
        }
    
    def get_all_licenses(self) -> Dict[str, Dict[str, Any]]:
        results = self.collection.get()
        
        output = {}
        for i, lid in enumerate(results["ids"]):
            output[lid] = {
                "document": results["documents"][i],
                "metadata": results["metadatas"][i],
            }
        return output


_rag_instance: Optional[LicenseRAG] = None


def get_rag_instance(persist_directory: str = "./chromadb_data") -> LicenseRAG:
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = LicenseRAG(persist_directory)
    return _rag_instance
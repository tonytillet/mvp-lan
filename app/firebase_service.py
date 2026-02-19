from typing import Optional, Dict, Any
from app.firestore import db

class FirebaseService:
    """Service class for Firebase Firestore operations"""
    
    def __init__(self):
        self.db = db
    
    async def create_document(self, collection: str, data: Dict[str, Any], document_id: Optional[str] = None) -> str:
        """Create a new document in Firestore"""
        try:
            if document_id:
                doc_ref = self.db.collection(collection).document(document_id)
                doc_ref.set(data)
                return document_id
            else:
                doc_ref = self.db.collection(collection).add(data)
                return doc_ref[1].id
        except Exception as e:
            raise Exception(f"Error creating document: {e}")
    
    async def get_document(self, collection: str, document_id: str) -> Optional[Dict[str, Any]]:
        """Get a document from Firestore"""
        try:
            doc_ref = self.db.collection(collection).document(document_id)
            doc = doc_ref.get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            raise Exception(f"Error getting document: {e}")
    
    async def update_document(self, collection: str, document_id: str, data: Dict[str, Any]) -> bool:
        """Update a document in Firestore"""
        try:
            doc_ref = self.db.collection(collection).document(document_id)
            doc_ref.update(data)
            return True
        except Exception as e:
            raise Exception(f"Error updating document: {e}")
    
    async def delete_document(self, collection: str, document_id: str) -> bool:
        """Delete a document from Firestore"""
        try:
            doc_ref = self.db.collection(collection).document(document_id)
            doc_ref.delete()
            return True
        except Exception as e:
            raise Exception(f"Error deleting document: {e}")
    
    async def query_documents(self, collection: str, where_clause: Optional[tuple] = None, limit: Optional[int] = None) -> list:
        """Query documents from Firestore"""
        try:
            query = self.db.collection(collection)
            
            if where_clause:
                field, operator, value = where_clause
                query = query.where(field, operator, value)
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            raise Exception(f"Error querying documents: {e}")

# Create a singleton instance
firebase_service = FirebaseService()

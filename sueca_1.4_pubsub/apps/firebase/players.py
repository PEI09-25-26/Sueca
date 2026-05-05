import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import os
from dotenv import load_dotenv
import json

load_dotenv()

class BD:
    def __init__(self):
        service_account_key_json_str = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')

        if not service_account_key_json_str:
            raise ValueError("A variável de ambiente 'FIREBASE_SERVICE_ACCOUNT_KEY' não está definida.")

        cred_dict = json.loads(service_account_key_json_str)
        cred = credentials.Certificate(cred_dict)

        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)

        self.db = firestore.client()

    def get_document(self, collection_path, document_id):
        doc_ref = self.db.collection(collection_path).document(document_id)
        doc = doc_ref.get()
        if doc.exists:
            print(f"Documento encontrado no caminho: {collection_path}/{document_id}")
            return doc.to_dict()
        else:
            print(f"Documento não encontrado no caminho: {collection_path}/{document_id}")
            return None

    def add_document(self, collection_path, data):
        doc_ref = self.db.collection(collection_path).add(data)
        print(f"Documento adicionado com ID: {doc_ref[1].id} na coleção: {collection_path}")
        return doc_ref[1].id # doc_ref é uma tupla (timestamp, document_reference)

    def set_document(self, collection_path, document_id, data, merge=False):
        doc_ref = self.db.collection(collection_path).document(document_id)
        doc_ref.set(data, merge=merge)
        print(f"Documento {document_id} definido (merge={merge}) na coleção: {collection_path}")

    def update_document(self, collection_path, document_id, data):
        doc_ref = self.db.collection(collection_path).document(document_id)
        doc_ref.update(data)
        print(f"Documento {document_id} atualizado na coleção: {collection_path}")

    def delete_document(self, collection_path, document_id):
        self.db.collection(collection_path).document(document_id).delete()
        print(f"Documento {document_id} deletado da coleção: {collection_path}")

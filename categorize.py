from dataclasses import dataclass
import json
from typing import List
from vecstore import collection


@dataclass(init=True)
class DocCategory:
    category: str
    distance: float
    id: str


@dataclass(init=True)
class Doc:
    code: str
    categories: List[DocCategory]

    @property
    def distinct_categories(self) -> List[str]:
        return list(set([category.category for category in self.categories]))
    
    def get_id_of_category(self, category: str) -> str:
        min_distance = float("inf")
        doc = None
        for doc_category in self.categories:
            if doc_category.category == category and doc_category.distance < min_distance:
                min_distance = doc_category.distance
                doc = doc_category.id
        if doc is None:
            raise ValueError(f"Could not find document with category {category}")
        return doc

    def count(self, category: str) -> int:
        return len([c for c in self.categories if c.category == category])


def classify_doc(doc: Doc) -> str:
    if len(doc.distinct_categories) == 1:
        return doc.distinct_categories[0]

    return "NOCRYPTO"


def classify_file(file_path: str, print_step = False) -> dict:
    with open(file_path) as f:
        documents = collection.query(
            query_texts=[f.read()],
            n_results=4
        )
        _id = documents.get("ids")[0]
        category = documents.get("metadatas")[0]
        distance = documents.get("distances")[0]
        response = {
            "categories": category,
            "distances": distance,
            "ids": _id
        }
        if print_step:
            json_data = json.dumps(
                response, 
                indent=4, 
                sort_keys=True, 
                skipkeys=True
            )
            print(json_data)
        return response


if __name__ == '__main__':
    import sys
    file_path = sys.argv[1]
    classify_file(file_path, print_step=True)

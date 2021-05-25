from rasa.shared.core.slots import Slot
import json
from services.api import list_categories

categories = json.load(open("services/categories.json", "r"))


class InsuranceCategorySlot(Slot):

    def feature_dimensionality(self) -> int:
        return 0;

    def as_feature(self):
        return list_categories(categories)
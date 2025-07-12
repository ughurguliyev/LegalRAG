"""Law code mapping for Azerbaijan legal documents"""

from typing import Dict


class LawCodeMapper:
    """Maps PDF filenames to law codes and names"""

    LAW_CODES = {
        "family-law-code.pdf": {
            "code": "family",
            "name_az": "Ailə Məcəlləsi",
            "name_en": "Family Law Code",
        },
        "criminal_law_code.pdf": {
            "code": "criminal",
            "name_az": "Cinayət Məcəlləsi",
            "name_en": "Criminal Law Code",
        },
        "civil_law_code.pdf": {
            "code": "civil",
            "name_az": "Mülki Məcəllə",
            "name_en": "Civil Law Code",
        },
        "criminal_procedure_law_code.pdf": {
            "code": "criminal_procedure",
            "name_az": "Cinayət Prosessual Məcəlləsi",
            "name_en": "Criminal Procedure Code",
        },
        "civil_procedure_law_code.pdf": {
            "code": "civil_procedure",
            "name_az": "Mülki Prosessual Məcəllə",
            "name_en": "Civil Procedure Code",
        },
        "labor_law_code.pdf": {
            "code": "labor",
            "name_az": "Əmək Məcəlləsi",
            "name_en": "Labor Law Code",
        },
        "administrative_offenses_law_code.pdf": {
            "code": "administrative_offenses",
            "name_az": "İnzibati Xətalar Məcəlləsi",
            "name_en": "Administrative Offenses Code",
        },
        "administrative_procedure_law_code.pdf": {
            "code": "administrative_procedure",
            "name_az": "İnzibati Prosedur Məcəlləsi",
            "name_en": "Administrative Procedure Code",
        },
        "competition_law_code.pdf": {
            "code": "competition",
            "name_az": "Rəqabət Məcəlləsi",
            "name_en": "Competition Law Code",
        },
        "customs_law_code.pdf": {
            "code": "customs",
            "name_az": "Gömrük Məcəlləsi",
            "name_en": "Customs Code",
        },
        "election_law_code.pdf": {
            "code": "election",
            "name_az": "Seçki Məcəlləsi",
            "name_en": "Election Code",
        },
        "execution_of_sentences_law_code.pdf": {
            "code": "execution",
            "name_az": "Cəzaların İcrası Məcəlləsi",
            "name_en": "Execution of Sentences Code",
        },
        "forest_law_code.pdf": {
            "code": "forest",
            "name_az": "Meşə Məcəlləsi",
            "name_en": "Forest Code",
        },
        "housing_law_code.pdf": {
            "code": "housing",
            "name_az": "Mənzil Məcəlləsi",
            "name_en": "Housing Code",
        },
        "land_law_code.pdf": {
            "code": "land",
            "name_az": "Torpaq Məcəlləsi",
            "name_en": "Land Code",
        },
        "merchant_shipping_law_code.pdf": {
            "code": "merchant_shipping",
            "name_az": "Ticarət Gəmiçiliyi Məcəlləsi",
            "name_en": "Merchant Shipping Code",
        },
        "migration_law_code.pdf": {
            "code": "migration",
            "name_az": "Miqrasiya Məcəlləsi",
            "name_en": "Migration Code",
        },
        "urban_planning_and_construction_law_code.pdf": {
            "code": "urban_planning",
            "name_az": "Şəhərsalma və Tikinti Məcəlləsi",
            "name_en": "Urban Planning and Construction Code",
        },
        "water_law_code.pdf": {
            "code": "water",
            "name_az": "Su Məcəlləsi",
            "name_en": "Water Code",
        },
    }

    @classmethod
    def get_law_info(cls, filename: str) -> Dict[str, str]:
        """Get law code info from filename"""
        return cls.LAW_CODES.get(
            filename,
            {
                "code": "unknown",
                "name_az": "Naməlum Məcəllə",
                "name_en": "Unknown Code",
            },
        )
